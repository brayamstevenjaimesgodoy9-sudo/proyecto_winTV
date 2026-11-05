from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .forms import IngresoAlmacenForm, RegistroProductoForm
from .models import MovimientoAlmacen, Producto


@login_required
def inicio_almacen(request):

    if not (
        request.user.groups.filter(name="ADMINISTRADOR").exists()
        or request.user.groups.filter(name="ALMACEN").exists()
    ):
        return HttpResponseForbidden(
            "No tienes permisos para acceder al almacén."
        )

    producto_form = RegistroProductoForm()
    ingreso_form = IngresoAlmacenForm()

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
                        producto.stock_minimo = 0
                        producto.activo = 1
                        producto.save()

                    messages.success(
                        request,
                        "Producto registrado correctamente."
                    )
                    return redirect("inicio_almacen")

                except Exception:
                    messages.error(
                        request,
                        "No se pudo registrar el producto. "
                        "Verifica que el código no esté repetido "
                        "y que los datos sean correctos."
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

                        producto.stock_actual += cantidad
                        producto.save(update_fields=["stock_actual"])

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

                except Exception:
                    messages.error(
                        request,
                        "No se pudo registrar el ingreso. "
                        "Verifica la conexión y las tablas de Oracle."
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
            "movimientos": movimientos,
            "productos": productos,
        }
    )
