
from django.urls import path

from . import views
from . import diagnostico_views
from . import asignacion_views

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
    # ==========================================
    # HU-15: ASIGNAR ORDENES A TECNICOS
    # ==========================================
    path(
        'asignar-orden/',
        asignacion_views.asignar_orden_tecnico,
        name='asignar_orden_tecnico'
    ),

    # ==========================================
    # HU-15: EDITAR ASIGNACIÓN DE TÉCNICO
    # ==========================================
    path(
        "asignaciones/<int:pk>/editar/",
        asignacion_views.editar_asignacion_tecnico,
        name="editar_asignacion_tecnico"
    ),
]
