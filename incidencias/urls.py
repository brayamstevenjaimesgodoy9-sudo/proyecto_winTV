
from django.urls import path

from . import views
from . import diagnostico_views

app_name = 'incidencias'

urlpatterns = [
    # ==========================================
    # HU-13: REGISTRAR INCIDENCIAS
    # ==========================================
    path(
        'registrar/',
        views.registrar_incidencia,
        name='registrar'
    ),

    # ==========================================
    # HU-13 / HU-14: CONSULTAR Y FILTRAR
    # ==========================================
    path(
        'listar/',
        views.listar_incidencias,
        name='listar'
    ),

    # ==========================================
    # HU-16: LISTAR ORDENES PARA DIAGNOSTICO
    # ==========================================
    path(
        'diagnosticos/',
        diagnostico_views.listar_ordenes_diagnostico,
        name='diagnosticos'
    ),

    # ==========================================
    # HU-16: REGISTRAR DIAGNOSTICO TECNICO
    # ==========================================
    path(
        'diagnosticos/<int:orden_id>/',
        diagnostico_views.registrar_diagnostico,
        name='diagnosticar'
    ),
]


# ==========================================
# HU-18: ESTADOS DE ÓRDENES DE TRABAJO
# ==========================================

from . import estado_orden_views

urlpatterns += [
    path(
        "ordenes/estados/",
        estado_orden_views.listar_estados_orden,
        name="estados_orden",
    ),

    path(
        "ordenes/estados/<int:orden_id>/",
        estado_orden_views.actualizar_estado_orden,
        name="actualizar_estado_orden",
    ),
]

# HU-19: Historial y detalle de incidencias (solo lectura)
from . import historial_views

urlpatterns += [
    path("historial/", historial_views.historial_incidencias, name="historial"),
    path("historial/<int:incidencia_id>/", historial_views.detalle_historial, name="historial_detalle"),
]
