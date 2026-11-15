
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import DatabaseError, transaction
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from almacen.models import (
    OrdenTrabajo,
    AsignacionTecnico,
)

from .estado_orden_forms import (
    EstadoOrdenForm,
    TRANSICIONES,
)


# ==========================================
# HU-18: VERIFICAR PERMISOS
# ==========================================

def verificar_permiso_estado(request):

    roles = {
        nombre.strip().upper()
        for nombre in request.user.groups.values_list(
            "name", flat=True
        )
    }

    es_admin = (
        request.user.is_superuser
        or "ADMINISTRADOR" in roles
    )

    es_tecnico = "TECNICO" in roles

    if not (es_admin or es_tecnico):
        raise PermissionDenied(
            "No tienes permiso para gestionar "
            "estados de órdenes de trabajo."
        )

    return es_admin


def verificar_asignacion(request, orden, es_admin):

    if es_admin:
        return

    asignado = AsignacionTecnico.objects.filter(
        orden_id=orden.pk,
        tecnico_id=request.user.pk,
    ).exists()

    if not asignado:
        raise PermissionDenied(
            "No estás asignado a esta orden."
        )


# ==========================================
# HU-18: LISTAR ÓRDENES
# ==========================================

@login_required
def listar_estados_orden(request):

    es_admin = verificar_permiso_estado(request)

    ordenes = OrdenTrabajo.objects.all().order_by(
        "-fecha_creacion"
    )

    if not es_admin:
        asignadas = AsignacionTecnico.objects.filter(
            tecnico_id=request.user.pk
        ).values("orden_id")

        ordenes = ordenes.filter(
            pk__in=asignadas
        )

    paginador = Paginator(ordenes, 15)

    pagina = paginador.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "incidencias/estados_orden.html",
        {
            "pagina": pagina,
        }
    )


# ==========================================
# HU-18: ACTUALIZAR ESTADO
# ==========================================

@login_required
def actualizar_estado_orden(request, orden_id):

    es_admin = verificar_permiso_estado(request)

    orden = get_object_or_404(
        OrdenTrabajo,
        pk=orden_id
    )

    verificar_asignacion(
        request,
        orden,
        es_admin
    )

    if request.method == "POST":

        try:
            with transaction.atomic():

                # Bloquear la orden durante la edición
                orden = get_object_or_404(
                    OrdenTrabajo.objects.select_for_update(),
                    pk=orden_id
                )

                verificar_asignacion(
                    request,
                    orden,
                    es_admin
                )

                formulario = EstadoOrdenForm(
                    request.POST,
                    estado_actual=orden.estado,
                )

                if formulario.is_valid():

                    nuevo_estado = (
                        formulario.cleaned_data["estado"]
                    )

                    orden.estado = nuevo_estado

                    # Actualizar solo el estado.
                    # No alterar diagnóstico ni solución.
                    orden.save(
                        update_fields=["estado"]
                    )

                    messages.success(
                        request,
                        "Estado actualizado correctamente."
                    )

                    return redirect(
                        "incidencias:estados_orden"
                    )

        except DatabaseError:
            messages.error(
                request,
                "No se pudo actualizar el estado "
                "en Oracle."
            )

    else:
        formulario = EstadoOrdenForm(
            estado_actual=orden.estado
        )

    return render(
        request,
        "incidencias/actualizar_estado.html",
        {
            "orden": orden,
            "formulario": formulario,
            "puede_cambiar": bool(
                TRANSICIONES.get(orden.estado, ())
            ),
        }
    )
