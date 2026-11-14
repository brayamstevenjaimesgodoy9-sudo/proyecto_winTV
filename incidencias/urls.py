
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
