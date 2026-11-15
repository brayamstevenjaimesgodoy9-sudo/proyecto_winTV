"""HU-19: Consulta de incidencias y sus órdenes asociadas (solo lectura).

Usa tablas existentes: INCIDENCIA, TIPO_AVERIA y ORDEN_TRABAJO.
No representa una auditoría de cada transición histórica de estado.
"""

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_date

from almacen.models import OrdenTrabajo
from .models import Incidencia, TipoAveria


def _verificar_permiso(request):
    roles = {
        nombre.strip().upper()
        for nombre in request.user.groups.values_list("name", flat=True)
    }
    if not (
        request.user.is_superuser
        or roles.intersection({"ADMINISTRADOR", "TECNICO"})
    ):
        raise PermissionDenied("No tienes permiso para consultar el historial de incidencias.")


@login_required
def historial_incidencias(request):
    """Buscar, filtrar y paginar incidencias sin modificar datos."""
    _verificar_permiso(request)

    buscar = request.GET.get("buscar", "").strip()[:100]
    tipo = request.GET.get("tipo", "").strip()
    estado = request.GET.get("estado", "").strip()[:30]
    desde = request.GET.get("desde", "").strip()
    hasta = request.GET.get("hasta", "").strip()

    incidencias = (
        Incidencia.objects.select_related("tipo_averia")
        .order_by("-fecha_reporte", "-id_incidencia")
    )

    if buscar:
        condicion = Q(descripcion__icontains=buscar)
        if buscar.isdecimal():
            numero = int(buscar)
            condicion |= (
                Q(id_incidencia=numero)
                | Q(id_cliente=numero)
                | Q(id_contrato=numero)
            )
        incidencias = incidencias.filter(condicion)

    if tipo.isdecimal():
        incidencias = incidencias.filter(tipo_averia_id=int(tipo))

    if estado:
        incidencias = incidencias.filter(estado=estado)

    fecha_desde = parse_date(desde)
    fecha_hasta = parse_date(hasta)
    if fecha_desde:
        incidencias = incidencias.filter(fecha_reporte__date__gte=fecha_desde)
    if fecha_hasta:
        incidencias = incidencias.filter(fecha_reporte__date__lte=fecha_hasta)

    parametros = request.GET.copy()
    parametros.pop("page", None)

    pagina = Paginator(incidencias, 15).get_page(request.GET.get("page"))

    return render(
        request,
        "incidencias/historial.html",
        {
            "pagina": pagina,
            "tipos_averia": TipoAveria.objects.all().order_by("nombre"),
            "estados": Incidencia.objects.order_by().values_list(
                "estado", flat=True
            ).distinct(),
            "buscar": buscar,
            "tipo_seleccionado": tipo,
            "estado_seleccionado": estado,
            "desde": desde,
            "hasta": hasta,
            "filtros_url": parametros.urlencode(),
        },
    )


@login_required
def detalle_historial(request, incidencia_id):
    """Detalle de incidencia y órdenes asociadas (no historial de cambios)."""
    _verificar_permiso(request)

    incidencia = get_object_or_404(
        Incidencia.objects.select_related("tipo_averia"),
        pk=incidencia_id,
    )
    ordenes = OrdenTrabajo.objects.filter(
        id_incidencia=incidencia.pk
    ).order_by("fecha_creacion", "id_orden")

    return render(
        request,
        "incidencias/historial_detalle.html",
        {"incidencia": incidencia, "ordenes": ordenes},
    )
