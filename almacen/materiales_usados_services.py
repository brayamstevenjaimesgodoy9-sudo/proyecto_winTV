from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F

from .models import DetalleEntrega, OrdenTrabajo, AsignacionTecnico


def registrar_material_utilizado(
    *,
    detalle_id,
    cantidad,
    usuario,
):
    """
    HU-17: Registra material utilizado en una reparación.

    No descuenta nuevamente el stock del almacén.
    """

    # 1. Verificar permisos del usuario.
    if not usuario.is_authenticated or not (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=["ADMINISTRADOR", "TECNICO"]
        ).exists()
    ):
        raise PermissionDenied(
            "No tienes permisos para registrar materiales utilizados."
        )

    # 2. Validar los datos recibidos.
    if (
        not isinstance(detalle_id, int)
        or isinstance(detalle_id, bool)
        or detalle_id <= 0
    ):
        raise ValidationError("El detalle de entrega no es válido.")

    if (
        not isinstance(cantidad, int)
        or isinstance(cantidad, bool)
        or cantidad <= 0
    ):
        raise ValidationError(
            "La cantidad utilizada debe ser mayor que cero."
        )

    # 3. Ejecutar la operación dentro de una transacción.
    with transaction.atomic():

        try:
            detalle = (
                DetalleEntrega.objects
                .select_related("entrega", "producto")
                .get(pk=detalle_id)
            )
        except DetalleEntrega.DoesNotExist:
            raise ValidationError(
                "El material entregado no existe."
            )

        # 4. Bloquear la orden antes de modificar sus materiales.
        try:
            orden = (
                OrdenTrabajo.objects
                .select_for_update()
                .get(pk=detalle.entrega.orden_id)
            )
        except OrdenTrabajo.DoesNotExist:
            raise ValidationError(
                "La orden de trabajo no existe."
            )

        # 5. Verificar el estado de la orden.
        if orden.estado not in ("PROGRAMADA", "EN_PROCESO"):
            raise ValidationError(
                "La orden no permite registrar materiales utilizados."
            )

        # 6. Verificar que la entrega esté vigente.
        if detalle.entrega.estado != "ENTREGADA":
            raise ValidationError(
                "La entrega de materiales no está disponible."
            )
        # HU-17: Solo registrar productos de categoría MATERIAL
        if detalle.producto.categoria != "MATERIAL":
            raise ValidationError(
                "Solo se pueden registrar materiales utilizados."
            )
        # HU-17: Verificar que la orden sea de reparación
        if orden.tipo_orden != "REPARACION":
            raise ValidationError(
                "Solo se pueden registrar materiales de órdenes de reparación."
            )

        # 7. Verificar que el técnico corresponda a la entrega.
        if not (
            usuario.is_superuser
            or usuario.groups.filter(
                name="ADMINISTRADOR"
            ).exists()
            or detalle.entrega.tecnico_id == usuario.pk
        ):
            raise PermissionDenied(
                "No puedes registrar materiales de otro técnico."
            )

            # HU-17: Verificar la asignación vigente del técnico
    
        # HU-17: Verificar la asignación vigente del técnico.
        if not (
            usuario.is_superuser
            or usuario.groups.filter(name="ADMINISTRADOR").exists()
        ):
            asignacion_valida = AsignacionTecnico.objects.filter(
                orden_id=orden.pk,
                tecnico_id=usuario.pk,
                estado__in=["ASIGNADO", "EN_PROCESO"],
            ).exists()

            if not asignacion_valida:
                raise PermissionDenied(
                    "No tienes una asignación vigente para esta reparación."
                )

        # 8. Actualizar únicamente si hay cantidad disponible.
        actualizados = DetalleEntrega.objects.filter(
            pk=detalle.pk,
            cantidad_entregada__gte=(
                F("cantidad_utilizada")
                + F("cantidad_devuelta")
                + cantidad
            ),
        ).update(
            cantidad_utilizada=F("cantidad_utilizada") + cantidad
        )

        if actualizados != 1:
            raise ValidationError(
                "La cantidad supera los materiales disponibles."
            )

        detalle.refresh_from_db()

        return detalle
