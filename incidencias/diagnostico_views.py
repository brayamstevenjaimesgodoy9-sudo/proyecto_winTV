
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import DatabaseError, transaction
from django.shortcuts import get_object_or_404, redirect, render

from almacen.models import OrdenTrabajo, AsignacionTecnico
from .diagnostico_forms import DiagnosticoOrdenForm


def verificar_permiso(request):
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
            "No tienes permiso para registrar diagnósticos."
        )

    return es_admin


@login_required
def listar_ordenes_diagnostico(request):
    es_admin = verificar_permiso(request)

    ordenes = OrdenTrabajo.objects.filter(
        tipo_orden="REPARACION",
        id_incidencia__isnull=False,
    ).order_by("-fecha_creacion")

    if not es_admin:
        asignadas = AsignacionTecnico.objects.filter(
            tecnico_id=request.user.pk
        ).values("orden_id")

        ordenes = ordenes.filter(pk__in=asignadas)

    return render(
        request,
        "incidencias/diagnosticos.html",
        {"ordenes": ordenes}
    )


@login_required
def registrar_diagnostico(request, orden_id):
    es_admin = verificar_permiso(request)

    orden = get_object_or_404(
        OrdenTrabajo,
        pk=orden_id,
        tipo_orden="REPARACION",
        id_incidencia__isnull=False,
    )

    if not es_admin:
        asignado = AsignacionTecnico.objects.filter(
            orden_id=orden.pk,
            tecnico_id=request.user.pk,
        ).exists()

        if not asignado:
            raise PermissionDenied(
                "No estás asignado a esta orden."
            )

    formulario = DiagnosticoOrdenForm(
        request.POST or None,
        instance=orden,
    )

    if request.method == "POST":
        if formulario.is_valid():
            try:
                with transaction.atomic():
                    registro = formulario.save(commit=False)

                    registro.save(update_fields=[
                        "diagnostico",
                        "solucion",
                        "observaciones",
                    ])

            except DatabaseError:
                messages.error(
                    request,
                    "No se pudo guardar el diagnóstico "
                    "en Oracle."
                )
            else:
                messages.success(
                    request,
                    "Diagnóstico registrado correctamente."
                )

                return redirect(
                    "incidencias:diagnosticos"
                )

    return render(
        request,
        "incidencias/diagnosticar.html",
        {
            "formulario": formulario,
            "orden": orden,
        }
    )
