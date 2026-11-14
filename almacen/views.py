import logging

from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import DatabaseError, transaction
from django.db.models import F
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .forms import (
    IngresoAlmacenForm,
    RegistroProductoForm,
    ConfigurarStockMinimoForm,
)
from .models import MovimientoAlmacen, Producto


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
            "movimientos": movimientos,
            "productos": productos,
        }
    )
