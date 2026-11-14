from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from .models import (
    Producto,
    MovimientoAlmacen,
    OrdenTrabajo,
    AsignacionTecnico,
    EntregaMaterial,
    DetalleEntrega,
)


def registrar_salida_materiales(
    *,
    orden_id,
    tecnico_id,
    detalles,
    usuario,
    observaciones="",
):
    """
    Registra una entrega y descuenta el stock de forma atómica.

    detalles:
        [
            {"producto_id": 1, "cantidad": 2},
            {"producto_id": 2, "cantidad": 5},
        ]
    """

    if not usuario.is_authenticated or not (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=["ADMINISTRADOR", "ALMACEN"]
        ).exists()
    ):
        raise PermissionDenied(
            "No tienes permisos para registrar salidas."
        )

    if not isinstance(orden_id, int) or orden_id <= 0:
        raise ValidationError("Orden de trabajo no válida.")

    if not isinstance(tecnico_id, int) or tecnico_id <= 0:
        raise ValidationError("Técnico no válido.")

    if not isinstance(detalles, (list, tuple)) or not detalles:
        raise ValidationError(
            "Debes seleccionar al menos un producto."
        )

    if not isinstance(observaciones, str):
        raise ValidationError("Observaciones no válidas.")

    observaciones = observaciones.strip()

    if len(observaciones.encode("utf-8")) > 500:
        raise ValidationError(
            "Las observaciones no pueden superar 500 bytes."
        )

    productos = []
    productos_repetidos = set()

    for detalle in detalles:
        if not isinstance(detalle, dict):
            raise ValidationError(
                "Formato de producto no válido."
            )

        producto_id = detalle.get("producto_id")
        cantidad = detalle.get("cantidad")

        if (
            not isinstance(producto_id, int)
            or isinstance(producto_id, bool)
            or producto_id <= 0
        ):
            raise ValidationError("Producto no válido.")

        if (
            not isinstance(cantidad, int)
            or isinstance(cantidad, bool)
            or cantidad <= 0
            or cantidad > 9999999999
        ):
            raise ValidationError(
                "La cantidad debe ser un entero positivo válido."
            )

        if producto_id in productos_repetidos:
            raise ValidationError(
                "No puedes repetir un producto en la misma entrega."
            )

        productos_repetidos.add(producto_id)
        productos.append((producto_id, cantidad))

    # Un orden estable reduce el riesgo de bloqueos cruzados.
    productos.sort(key=lambda item: item[0])

    with transaction.atomic():

        try:
            orden = OrdenTrabajo.objects.select_for_update().get(
                pk=orden_id
            )
        except OrdenTrabajo.DoesNotExist:
            raise ValidationError(
                "La orden de trabajo no existe."
            )

        if orden.estado not in ("PROGRAMADA", "EN_PROCESO"):
            raise ValidationError(
                "La orden no permite entregas en su estado actual."
            )

        tecnico_valido = get_user_model().objects.filter(
            pk=tecnico_id,
            is_active=True,
            groups__name="TECNICO",
        ).exists()

        if not tecnico_valido:
            raise ValidationError(
                "El técnico no está activo o no tiene el rol TECNICO."
            )

        try:
            asignacion = (
                AsignacionTecnico.objects
                .select_for_update()
                .get(
                    orden_id=orden_id,
                    tecnico_id=tecnico_id,
                )
            )
        except AsignacionTecnico.DoesNotExist:
            raise ValidationError(
                "El técnico no está asignado a esta orden."
            )

        if asignacion.estado not in ("ASIGNADO", "EN_PROCESO"):
            raise ValidationError(
                "La asignación del técnico no está vigente."
            )

        entrega = EntregaMaterial.objects.create(
            orden_id=orden_id,
            tecnico_id=tecnico_id,
            fecha_entrega=timezone.now(),
            estado="ENTREGADA",
            observaciones=observaciones or None,
        )

        for producto_id, cantidad in productos:

            actualizados = Producto.objects.filter(
                pk=producto_id,
                activo=1,
                stock_actual__gte=cantidad,
            ).update(
                stock_actual=F("stock_actual") - cantidad
            )

            if actualizados != 1:
                raise ValidationError(
                    f"Stock insuficiente o producto no disponible "
                    f"(ID {producto_id})."
                )

            DetalleEntrega.objects.create(
                entrega=entrega,
                producto_id=producto_id,
                cantidad_entregada=cantidad,
                cantidad_utilizada=0,
                cantidad_devuelta=0,
            )

            MovimientoAlmacen.objects.create(
                producto_id=producto_id,
                id_usuario=usuario.pk,
                tipo_movimiento="SALIDA",
                cantidad=cantidad,
                fecha_movimiento=timezone.now(),
                motivo=f"Entrega a técnico - Orden #{orden_id}",
                observaciones=observaciones or None,
            )

        return entrega

def registrar_devolucion_materiales(
    *,
    entrega_id,
    detalles,
    usuario,
    observaciones="",
):
    """
    Registra devoluciones de materiales de una entrega.

    detalles:
        [
            {"detalle_id": 1, "cantidad": 2},
            {"detalle_id": 2, "cantidad": 1},
        ]

    El proceso completo es atómico.
    """

    if not usuario.is_authenticated or not (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=["ADMINISTRADOR", "ALMACEN"]
        ).exists()
    ):
        raise PermissionDenied(
            "No tienes permisos para registrar devoluciones."
        )

    if type(entrega_id) is not int or entrega_id <= 0:
        raise ValidationError("Entrega no válida.")

    if not isinstance(detalles, (list, tuple)) or not detalles:
        raise ValidationError(
            "Debes seleccionar al menos un material."
        )

    if not isinstance(observaciones, str):
        raise ValidationError("Observaciones no válidas.")

    observaciones = observaciones.strip()

    if len(observaciones.encode("utf-8")) > 500:
        raise ValidationError(
            "Las observaciones no pueden superar 500 bytes."
        )

    materiales = []
    identificadores = set()

    for elemento in detalles:
        if not isinstance(elemento, dict):
            raise ValidationError(
                "Formato de devolución no válido."
            )

        detalle_id = elemento.get("detalle_id")
        cantidad = elemento.get("cantidad")

        if type(detalle_id) is not int or detalle_id <= 0:
            raise ValidationError(
                "El detalle de entrega no es válido."
            )

        if (
            type(cantidad) is not int
            or cantidad <= 0
            or cantidad > 9999999999
        ):
            raise ValidationError(
                "La cantidad debe ser un entero positivo válido."
            )

        if detalle_id in identificadores:
            raise ValidationError(
                "No puedes repetir un material en la devolución."
            )

        identificadores.add(detalle_id)
        materiales.append((detalle_id, cantidad))

    # Orden consistente para reducir riesgos de bloqueos cruzados.
    materiales.sort(key=lambda elemento: elemento[0])

    with transaction.atomic():
        try:
            entrega = (
                EntregaMaterial.objects
                .select_for_update()
                .get(pk=entrega_id)
            )
        except EntregaMaterial.DoesNotExist:
            raise ValidationError(
                "La entrega de materiales no existe."
            )

        if entrega.estado not in ("ENTREGADA", "PARCIAL"):
            raise ValidationError(
                "La entrega no permite devoluciones "
                "en su estado actual."
            )

        for detalle_id, cantidad in materiales:
            try:
                detalle = (
                    DetalleEntrega.objects
                    .select_for_update()
                    .get(
                        pk=detalle_id,
                        entrega_id=entrega_id,
                    )
                )
            except DetalleEntrega.DoesNotExist:
                raise ValidationError(
                    "El material no pertenece a esta entrega."
                )

            disponible = (
                detalle.cantidad_entregada
                - detalle.cantidad_utilizada
                - detalle.cantidad_devuelta
            )

            if cantidad > disponible:
                raise ValidationError(
                    "La cantidad solicitada supera "
                    "el material disponible para devolución."
                )

            actualizados = DetalleEntrega.objects.filter(
                pk=detalle_id,
                entrega_id=entrega_id,
                cantidad_devuelta__lte=(
                    F("cantidad_entregada")
                    - F("cantidad_utilizada")
                    - cantidad
                ),
            ).update(
                cantidad_devuelta=F("cantidad_devuelta") + cantidad
            )

            if actualizados != 1:
                raise ValidationError(
                    "No fue posible actualizar "
                    "la cantidad devuelta."
                )

            stock_actualizado = Producto.objects.filter(
                pk=detalle.producto_id,
                stock_actual__lte=9999999999 - cantidad,
            ).update(
                stock_actual=F("stock_actual") + cantidad
            )

            if stock_actualizado != 1:
                raise ValidationError(
                    "No fue posible devolver el material "
                    "al inventario."
                )

            MovimientoAlmacen.objects.create(
                producto_id=detalle.producto_id,
                id_usuario=usuario.pk,
                tipo_movimiento="DEVOLUCION",
                cantidad=cantidad,
                fecha_movimiento=timezone.now(),
                motivo=f"Devolución de entrega #{entrega_id}",
                observaciones=observaciones or None,
            )

        return entrega
