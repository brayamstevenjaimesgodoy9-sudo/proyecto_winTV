"""
Vistas de consulta del módulo Almacén.

HU-12: reportes de movimientos.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import DatabaseError
from django.http import HttpResponseForbidden, HttpResponseNotAllowed
from django.shortcuts import render

from .forms import ReporteMovimientosForm
from .reportes import obtener_movimientos_reporte
from .exportaciones import exportar_movimientos_csv


logger = logging.getLogger(__name__)


@login_required
def reporte_movimientos(request):
    """Consulta paginada de movimientos de Almacén."""

    usuario = request.user

    autorizado = (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=["ADMINISTRADOR", "ALMACEN"]
        ).exists()
    )

    if not autorizado:
        return HttpResponseForbidden(
            "No tienes permisos para consultar reportes de almacén."
        )

    if request.method != "GET":
        return HttpResponseNotAllowed(["GET"])

    formulario = ReporteMovimientosForm(request.GET)
    pagina = None

    if formulario.is_valid():
        try:
            movimientos = obtener_movimientos_reporte(
                formulario.cleaned_data
            )

            if request.GET.get("formato") == "csv":
                return exportar_movimientos_csv(movimientos)

            paginador = Paginator(movimientos, 25)

            pagina = paginador.get_page(
                request.GET.get("pagina")
            )

            # Materializar únicamente los registros de esta página.
            pagina.object_list = list(pagina.object_list)

        except DatabaseError:
            logger.exception(
                "Error de Oracle al consultar reporte de movimientos"
            )

            messages.error(
                request,
                "No fue posible consultar los movimientos. "
                "Verifica la conexión con Oracle.",
            )

    return render(
        request,
        "almacen/reporte_movimientos.html",
        {
            "filtro_form": formulario,
            "pagina": pagina,
        },
    )
