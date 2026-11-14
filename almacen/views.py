
import logging

from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .forms import (
    IngresoAlmacenForm,
    RegistroProductoForm,
    ConfigurarStockMinimoForm,
    SalidaMaterialesForm,
    DetalleSalidaFormSet,
    DevolucionMaterialForm,
    AsignarEquipoClienteForm,
    RegistrarMaterialUtilizadoForm,
)

from .models import (
    MovimientoAlmacen,
    Producto,
    DetalleEntrega,
)
from .services import (
    registrar_salida_materiales,
    registrar_equipo_cliente,
    registrar_devolucion_materiales,
)
from .materiales_usados_services import registrar_material_utilizado

logger = logging.getLogger(__name__)


@login_required
def inicio_almacen(request):

    if not (
        request.user.is_superuser
        or request.user.groups.filter(name="ADMINISTRADOR").exists()
        or request.user.groups.filter(name="ALMACEN").exists()
    ):
        return HttpResponseForbidden(
            "No tienes permisos para acceder al almacén."
        )

    producto_form = RegistroProductoForm()
    ingreso_form = IngresoAlmacenForm()
    stock_minimo_form = ConfigurarStockMinimoForm()
    salida_form = SalidaMaterialesForm()
    detalle_salida_formset = DetalleSalidaFormSet(prefix="detalle")
    devolucion_form = DevolucionMaterialForm()

    if request.method == "POST":

        accion = request.POST.get("accion")

        # REGISTRAR PRODUCTO NUEVO
        if accion == "registrar_producto":

            producto_form = RegistroProductoForm(request.POST)

            if producto_form.is_valid():
                try:
                    with transaction.atomic():
                        producto = producto_form.save(commit=False)
                        producto.stock_actual = 0
                        producto.stock_minimo = producto_form.cleaned_data["stock_minimo"]
                        producto.activo = 1
                        producto.save()

                    messages.success(
                        request,
                        "Producto registrado correctamente."
                    )
                    return redirect("inicio_almacen")

                except DatabaseError:
                    logger.exception(
                        "Error de base de datos al registrar producto"
                    )
                    messages.error(
                        request,
                        "No se pudo registrar el producto. "
                        "Ocurrió un error de base de datos."
                    )

        # REGISTRAR INGRESO DE PRODUCTOS
        elif accion == "registrar_ingreso":

            ingreso_form = IngresoAlmacenForm(request.POST)

            if ingreso_form.is_valid():

                producto = ingreso_form.cleaned_data["producto"]
                cantidad = ingreso_form.cleaned_data["cantidad"]
                motivo = ingreso_form.cleaned_data["motivo"]
                observaciones = ingreso_form.cleaned_data["observaciones"]

                try:
                    with transaction.atomic():

                        actualizados = Producto.objects.filter(
                            pk=producto.pk,
                            activo=1,
                        ).update(
                            stock_actual=F("stock_actual") + cantidad
                        )

                        if actualizados != 1:
                            raise ValueError(
                                "El producto ya no está disponible."
                            )

                        MovimientoAlmacen.objects.create(
                            producto=producto,
                            id_usuario=request.user.id,
                            tipo_movimiento="ENTRADA",
                            cantidad=cantidad,
                            fecha_movimiento=timezone.now(),
                            motivo=motivo,
                            observaciones=observaciones or None,
                        )

                    messages.success(
                        request,
                        "Ingreso registrado correctamente."
                    )
                    return redirect("inicio_almacen")

                except ValueError:
                    messages.error(
                        request,
                        "No se pudo registrar el ingreso. "
                        "El producto ya no está disponible."
                    )

                except DatabaseError:
                    logger.exception(
                        "Error de base de datos al registrar ingreso"
                    )
                    messages.error(
                        request,
                        "No se pudo registrar el ingreso. "
                        "Ocurrió un error de base de datos."
                    )

        # HU-10: ACTUALIZAR STOCK MINIMO
        elif accion == "configurar_stock_minimo":

            stock_minimo_form = ConfigurarStockMinimoForm(request.POST)

            if stock_minimo_form.is_valid():
                producto = stock_minimo_form.cleaned_data["producto"]
                nuevo_minimo = stock_minimo_form.cleaned_data["stock_minimo"]

                try:
                    with transaction.atomic():
                        actualizados = Producto.objects.filter(
                            pk=producto.pk,
                            activo=1,
                        ).update(stock_minimo=nuevo_minimo)

                    if actualizados == 1:
                        messages.success(
                            request,
                            "Stock mínimo actualizado correctamente."
                        )
                        return redirect("inicio_almacen")

                    stock_minimo_form.add_error(
                        "producto",
                        "El producto seleccionado ya no está disponible."
                    )

                except DatabaseError:
                    messages.error(
                        request,
                        "No se pudo actualizar el stock mínimo. "
                        "Verifica la conexión con Oracle."
                    )

        # HU-08: REGISTRAR SALIDA A TÉCNICOS
        elif accion == "registrar_salida":
            salida_form = SalidaMaterialesForm(request.POST)
            detalle_salida_formset = DetalleSalidaFormSet(
                request.POST, prefix="detalle"
            )

            cabecera_valida = salida_form.is_valid()
            detalles_validos = detalle_salida_formset.is_valid()

            if cabecera_valida and detalles_validos:
                detalles = [
                    {
                        "producto_id": fila["producto"].pk,
                        "cantidad": fila["cantidad"],
                    }
                    for fila in detalle_salida_formset.cleaned_data
                    if fila and fila.get("producto") is not None
                ]

                try:
                    entrega = registrar_salida_materiales(
                        orden_id=salida_form.cleaned_data["orden"].pk,
                        tecnico_id=salida_form.cleaned_data["tecnico"].pk,
                        detalles=detalles,
                        usuario=request.user,
                        observaciones=salida_form.cleaned_data[
                            "observaciones"
                        ],
                    )

                except ValidationError as error:
                    salida_form.add_error(None, error)

                except DatabaseError:
                    logger.exception(
                        "Error de Oracle al registrar salida de almacén"
                    )
                    salida_form.add_error(
                        None,
                        "No se pudo registrar la salida. "
                        "Ocurrió un error de base de datos.",
                    )

                else:
                    messages.success(
                        request,
                        f"Salida #{entrega.pk} registrada correctamente.",
                    )
                    return redirect("inicio_almacen")

        # HU-11: REGISTRAR DEVOLUCIÓN DE MATERIALES
        elif accion == "registrar_devolucion":
            devolucion_form = DevolucionMaterialForm(request.POST)

            if devolucion_form.is_valid():
                detalle = devolucion_form.cleaned_data["detalle"]
                cantidad = devolucion_form.cleaned_data["cantidad"]
                observaciones = devolucion_form.cleaned_data[
                    "observaciones"
                ]

                try:
                    entrega = registrar_devolucion_materiales(
                        entrega_id=detalle.entrega_id,
                        detalles=[
                            {
                                "detalle_id": detalle.pk,
                                "cantidad": cantidad,
                            }
                        ],
                        usuario=request.user,
                        observaciones=observaciones,
                    )

                except ValidationError as error:
                    devolucion_form.add_error(None, error)

                except DatabaseError:
                    logger.exception(
                        "Error de Oracle al registrar devolución"
                    )
                    devolucion_form.add_error(
                        None,
                        "No se pudo registrar la devolución. "
                        "Ocurrió un error de base de datos.",
                    )

                else:
                    messages.success(
                        request,
                        f"Devolución de la entrega "
                        f"#{entrega.pk} registrada correctamente.",
                    )
                    return redirect("inicio_almacen")

    movimientos = MovimientoAlmacen.objects.select_related(
        "producto"
    ).order_by("-fecha_movimiento")

    productos = Producto.objects.filter(
        activo=1
    ).order_by("nombre")

    return render(
        request,
        "almacen/inicio.html",
        {
            "producto_form": producto_form,
            "ingreso_form": ingreso_form,
            "stock_minimo_form": stock_minimo_form,
            "salida_form": salida_form,
            "devolucion_form": devolucion_form,
            "detalle_salida_formset": detalle_salida_formset,
            "movimientos": movimientos,
            "productos": productos,
        }
    )


# ==========================================
# HU-09: ASOCIAR EQUIPOS ENTREGADOS A CLIENTE
# RESPONSABLE: JHAMPIER
# ==========================================

@login_required
def asignar_equipo_cliente(request):

    if not (
        request.user.is_superuser
        or request.user.groups.filter(
            name__in=["ADMINISTRADOR", "ALMACEN"]
        ).exists()
    ):
        return HttpResponseForbidden(
            "No tienes permisos para asociar equipos."
        )

    if request.method == "POST":
        form = AsignarEquipoClienteForm(request.POST)

        if form.is_valid():
            datos = form.cleaned_data

            try:
                equipo = registrar_equipo_cliente(
                    cliente_id=datos["cliente"].pk,
                    producto_id=datos["producto"].pk,
                    orden_id=datos["orden"].pk,
                    numero_serie=datos["numero_serie"] or "",
                    usuario=request.user,
                    observaciones=datos["observaciones"] or "",
                )

            except ValidationError as error:
                form.add_error(None, error)

            except PermissionDenied:
                return HttpResponseForbidden(
                    "No tienes permisos para realizar esta operación."
                )

            except DatabaseError:
                logger.exception(
                    "Error de Oracle al asociar equipo con cliente"
                )
                form.add_error(
                    None,
                    "No se pudo registrar la asociación. "
                    "Ocurrió un error de base de datos."
                )

            else:
                messages.success(
                    request,
                    f"Equipo #{equipo.pk} asociado correctamente."
                )
                return redirect("asignar_equipo_cliente")

    else:
        form = AsignarEquipoClienteForm()

    return render(
        request,
        "almacen/asignar_equipo.html",
        {
            "form": form,
        }
    )


# ==========================================
# HU-17: REGISTRAR MATERIALES UTILIZADOS
# RESPONSABLE: BRAYAM
# ==========================================

@login_required
def registrar_materiales_usados(request):

    es_administrador = (
        request.user.is_superuser
        or request.user.groups.filter(
            name="ADMINISTRADOR"
        ).exists()
    )

    es_tecnico = request.user.groups.filter(
        name="TECNICO"
    ).exists()

    if not (es_administrador or es_tecnico):
        return HttpResponseForbidden(
            "No tienes permisos para registrar materiales utilizados."
        )

    detalles = DetalleEntrega.objects.select_related(
        "entrega", "producto"
    ).filter(
        entrega__estado="ENTREGADA",
        entrega__orden__estado__in=[
            "PROGRAMADA", "EN_PROCESO"
        ],
        producto__categoria="MATERIAL",
    )

    if not es_administrador:
        detalles = detalles.filter(
            entrega__tecnico_id=request.user.pk
        )

    detalles = detalles.order_by("id_detalle")
    detalles = detalles.annotate(
    disponible=(
        F("cantidad_entregada")
        - F("cantidad_utilizada")
        - F("cantidad_devuelta")
    )
)
    if request.method == "POST":
        form = RegistrarMaterialUtilizadoForm(request.POST)

        if form.is_valid():
            detalle_id = form.cleaned_data["detalle_id"]
            cantidad = form.cleaned_data["cantidad"]

            try:
                detalle = registrar_material_utilizado(
                    detalle_id=detalle_id,
                    cantidad=cantidad,
                    usuario=request.user,
                )

            except ValidationError as error:
                form.add_error(None, error)

            except PermissionDenied:
                return HttpResponseForbidden(
                    "No tienes permisos para registrar este material."
                )

            except DatabaseError:
                logger.exception(
                    "Error de Oracle al registrar materiales utilizados"
                )
                form.add_error(
                    None,
                    "No se pudo guardar el registro en Oracle."
                )

            else:
                messages.success(
    request,
    (
        f"Se registró {cantidad} unidad utilizada"
        if cantidad == 1
        else f"Se registraron {cantidad} unidades utilizadas"
    ) + f" del material {detalle.producto.nombre}."
)
                return redirect("registrar_materiales_usados")

    else:
        form = RegistrarMaterialUtilizadoForm()

    return render(
        request,
        "almacen/materiales_usados.html",
        {
            "form": form,
            "detalles": detalles,
        }
    )