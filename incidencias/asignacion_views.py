from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import render, redirect
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from almacen.models import OrdenTrabajo, AsignacionTecnico

from .asignacion_forms import (
    AsignacionTecnicoForm,
    EditarAsignacionTecnicoForm,
)


# ==========================================
# HU-15: ASIGNAR ÓRDENES DE TRABAJO
# ==========================================

@login_required
def asignar_orden_tecnico(request):

    # 1. Verificar permisos del usuario
    if not (
        request.user.is_superuser
        or request.user.groups.filter(
            name="ADMINISTRADOR"
        ).exists()
    ):
        raise PermissionDenied(
            "No tienes permiso para asignar técnicos."
        )

    # 2. Preparar el formulario
    formulario = AsignacionTecnicoForm(
        request.POST if request.method == "POST" else None
    )

    # 3. Procesar el formulario
    if request.method == "POST":

        if formulario.is_valid():

            orden = formulario.cleaned_data["orden"]
            tecnico = formulario.cleaned_data["tecnico"]
            observaciones = formulario.cleaned_data["observaciones"]

            # 4. Evitar asignaciones duplicadas
            try:
                duplicado = AsignacionTecnico.objects.filter(
                    orden=orden,
                    tecnico=tecnico
                ).exists()

                if duplicado:
                    formulario.add_error(
                        "tecnico",
                        "Este técnico ya está asignado a esta orden."
                    )

                else:
                    # 5. Registrar la asignación en Oracle
                    with transaction.atomic():

                        # Volver a verificar el estado de la orden
                        orden_actual = (
                            OrdenTrabajo.objects
                            .select_for_update()
                            .get(pk=orden.pk)
                        )

                        if orden_actual.estado not in (
                            "PENDIENTE",
                            "PROGRAMADA"
                        ):
                            formulario.add_error(
                                "orden",
                                "Esta orden ya no está disponible para asignación."
                            )

                        elif AsignacionTecnico.objects.filter(
                            orden=orden_actual,
                            tecnico=tecnico
                        ).exists():
                            formulario.add_error(
                                "tecnico",
                                "Este técnico ya está asignado a esta orden."
                            )

                        else:
                            AsignacionTecnico.objects.create(
                                orden=orden_actual,
                                tecnico=tecnico,
                                fecha_asignacion=timezone.now(),
                                estado="ASIGNADO",
                                observaciones=observaciones
                            )

                            messages.success(
                                request,
                                "Orden de trabajo asignada correctamente."
                            )

                            return redirect(
                                "incidencias:asignar_orden_tecnico"
                            )

            except (DatabaseError, IntegrityError):
                messages.error(
                    request,
                    "Ocurrió un error al registrar la asignación."
                )

        else:
            messages.error(
                request,
                "Por favor, corrige los errores del formulario."
            )

    # 6. Consultar las asignaciones registradas en Oracle
    asignaciones = (
        AsignacionTecnico.objects
        .select_related("orden", "tecnico")
        .order_by("-fecha_asignacion", "-id_asignacion")
    )

    # 7. Mostrar el formulario y las asignaciones
    return render(
        request,
        "incidencias/asignar_orden.html",
        {
            "formulario": formulario,
            "asignaciones": asignaciones,
        }
    )


# ==========================================
# HU-15: EDITAR ASIGNACIÓN DE TÉCNICO
# ==========================================

@login_required
def editar_asignacion_tecnico(request, pk):

    # 1. Verificar permisos de administrador
    if not (
        request.user.is_superuser
        or request.user.groups.filter(
            name="ADMINISTRADOR"
        ).exists()
    ):
        raise PermissionDenied(
            "No tienes permiso para editar asignaciones."
        )

    # 2. Buscar la asignación por su ID
    try:
        asignacion = (
            AsignacionTecnico.objects
            .select_related("orden", "tecnico")
            .get(pk=pk)
        )
    except AsignacionTecnico.DoesNotExist:
        raise Http404("La asignación no existe.")

    # 3. Preparar el formulario con los datos actuales
    formulario = EditarAsignacionTecnicoForm(
        request.POST if request.method == "POST" else None,
        initial={
            "tecnico": asignacion.tecnico,
            "observaciones": asignacion.observaciones or "",
        }
    )

    # 4. Procesar los cambios
    if request.method == "POST":

        if formulario.is_valid():

            nuevo_tecnico = formulario.cleaned_data["tecnico"]
            observaciones = formulario.cleaned_data["observaciones"]

            try:
                with transaction.atomic():

                    # Bloquear el registro mientras se modifica
                    asignacion_actual = (
                        AsignacionTecnico.objects
                        .select_for_update()
                        .get(pk=pk)
                    )

                    # No permitir editar asignaciones canceladas
                    if asignacion_actual.estado != "ASIGNADO":
                        formulario.add_error(
                            None,
                            "Solo se pueden editar asignaciones en estado ASIGNADO."
                        )

                    # Evitar asignar el mismo técnico dos veces
                    elif AsignacionTecnico.objects.filter(
                        orden=asignacion_actual.orden,
                        tecnico=nuevo_tecnico
                    ).exclude(pk=pk).exists():
                        formulario.add_error(
                            "tecnico",
                            "Este técnico ya está asignado a esta orden."
                        )

                    else:
                        # Actualizar los datos sin cambiar el ID
                        # ni la fecha original de asignación
                        asignacion_actual.tecnico = nuevo_tecnico
                        asignacion_actual.observaciones = observaciones

                        asignacion_actual.save(
                            update_fields=[
                                "tecnico",
                                "observaciones"
                            ]
                        )

                        messages.success(
                            request,
                            "Asignación actualizada correctamente."
                        )

                        return redirect(
                            "incidencias:asignar_orden_tecnico"
                        )

            except DatabaseError:
                messages.error(
                    request,
                    "Ocurrió un error al actualizar la asignación."
                )

        else:
            messages.error(
                request,
                "Corrige los errores del formulario."
            )

    # 5. Mostrar el formulario de edición
    return render(
        request,
        "incidencias/editar_asignacion.html",
        {
            "formulario": formulario,
            "asignacion": asignacion,
        }
    )
