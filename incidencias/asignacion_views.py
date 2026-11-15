
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.db import DatabaseError, IntegrityError, transaction
from django.utils import timezone

from almacen.models import OrdenTrabajo, AsignacionTecnico
from .asignacion_forms import AsignacionTecnicoForm


# HU-15: ASIGNAR ORDENES DE TRABAJO A TECNICOS

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
                        orden_actual = OrdenTrabajo.objects.select_for_update().get(
                            pk=orden.pk
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

    # 6. Mostrar el formulario
    return render(
        request,
        "incidencias/asignar_orden.html",
        {
            "formulario": formulario
        }
    )
