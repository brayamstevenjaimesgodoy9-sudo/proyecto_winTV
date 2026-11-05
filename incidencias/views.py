
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import DatabaseError, transaction
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator

from .models import Incidencia
from .forms import IncidenciaForm


# ==========================================
# HU-13: REGISTRAR INCIDENCIAS
# ==========================================

@login_required
def registrar_incidencia(request):

    roles_permitidos = {"ADMINISTRADOR", "TECNICO"}

    roles_usuario = {
        nombre.strip().upper()
        for nombre in request.user.groups.values_list(
            "name", flat=True
        )
    }

    if not (
        request.user.is_superuser
        or roles_usuario.intersection(roles_permitidos)
    ):
        raise PermissionDenied(
            "No tienes permiso para registrar incidencias."
        )

    formulario = IncidenciaForm(
        request.POST or None
    )

    if request.method == 'POST':

        if formulario.is_valid():
            try:
                with transaction.atomic():
                    incidencia = formulario.save(
                        commit=False
                    )

                    incidencia.estado = 'REGISTRADA'
                    incidencia.save()

            except DatabaseError:
                messages.error(
                    request,
                    "No se pudo registrar la incidencia. "
                    "Verifica la operación en Oracle."
                )

            else:
                messages.success(
                    request,
                    "Incidencia registrada correctamente."
                )

                return redirect(
                    'incidencias:registrar'
                )

    return render(
        request,
        'incidencias/registrar.html',
        {
            'formulario': formulario
        }
    )


# ==========================================
# HU-13: LISTAR INCIDENCIAS
# ==========================================

@login_required
def listar_incidencias(request):

    roles_permitidos = {"ADMINISTRADOR", "TECNICO"}

    roles_usuario = {
        nombre.strip().upper()
        for nombre in request.user.groups.values_list(
            "name", flat=True
        )
    }

    if not (
        request.user.is_superuser
        or roles_usuario.intersection(roles_permitidos)
    ):
        raise PermissionDenied(
            "No tienes permiso para consultar incidencias."
        )

    incidencias = (
        Incidencia.objects
        .select_related('tipo_averia')
        .order_by('-fecha_reporte')
    )

    paginador = Paginator(incidencias, 15)

    pagina = paginador.get_page(
        request.GET.get('page')
    )

    return render(
        request,
        'incidencias/listar.html',
        {
            'pagina': pagina,
        }
    )
