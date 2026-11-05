
from django.shortcuts import render, redirect
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden

from .forms import IngresoAlmacenForm
from .models import MovimientoAlmacen


@login_required
def inicio_almacen(request):

    if not (
        request.user.groups.filter(name="ADMINISTRADOR").exists()
        or request.user.groups.filter(name="ALMACEN").exists()
    ):
        return HttpResponseForbidden(
            "No tienes permisos para acceder al almacén."
        )

    if request.method == "POST":
        form = IngresoAlmacenForm(request.POST)

        if form.is_valid():
            producto = form.cleaned_data["producto"]
            cantidad = form.cleaned_data["cantidad"]
            motivo = form.cleaned_data["motivo"]
            observaciones = form.cleaned_data["observaciones"]

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

    else:
        form = IngresoAlmacenForm()

    movimientos = MovimientoAlmacen.objects.select_related(
        "producto"
    ).order_by("-fecha_movimiento")

    return render(
        request,
        "almacen/inicio.html",
        {
            "form": form,
            "movimientos": movimientos,
        }
    )
