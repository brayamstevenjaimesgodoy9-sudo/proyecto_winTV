"""
Consultas de reportes del módulo de Almacén.

HU-12: consulta y filtrado de movimientos de inventario.
"""

from datetime import datetime, time

from django.utils import timezone

from .models import MovimientoAlmacen


def obtener_movimientos_reporte(filtros):
    """
    Construye un QuerySet de movimientos aplicando filtros validados.

    filtros debe proceder de ReporteMovimientosForm.cleaned_data.
    No modifica registros de Oracle.
    """

    movimientos = (
        MovimientoAlmacen.objects
        .select_related("producto")
        .order_by("-fecha_movimiento", "-pk")
    )

    zona_horaria = timezone.get_current_timezone()

    fecha_desde = filtros.get("fecha_desde")
    fecha_hasta = filtros.get("fecha_hasta")
    tipo = filtros.get("tipo_movimiento")
    producto = filtros.get("producto")

    if fecha_desde:
        inicio = timezone.make_aware(
            datetime.combine(fecha_desde, time.min),
            zona_horaria,
        )
        movimientos = movimientos.filter(
            fecha_movimiento__gte=inicio
        )

    if fecha_hasta:
        fin = timezone.make_aware(
            datetime.combine(fecha_hasta, time.max),
            zona_horaria,
        )
        movimientos = movimientos.filter(
            fecha_movimiento__lte=fin
        )

    if tipo:
        movimientos = movimientos.filter(
            tipo_movimiento=tipo
        )

    if producto is not None:
        movimientos = movimientos.filter(
            producto_id=producto.pk
        )

    return movimientos
