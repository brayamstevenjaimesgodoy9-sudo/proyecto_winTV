
from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [

    # HU-01: REGISTRAR CLIENTES
    path(
        "registrar/",
        views.registrar_cliente,
        name="registrar"
    ),

    # HU-06: BUSCAR CLIENTES
    path(
        "buscar/",
        views.buscar_clientes,
        name="buscar"
    ),

    # HU-04: CONSULTAR HISTORIAL
    path(
        "historial/<int:cliente_id>/",
        views.historial_cliente,
        name="historial"
    ),

    # EDITAR CLIENTE
    path(
        "editar/<int:cliente_id>/",
        views.editar_cliente,
        name="editar"
    ),

    # ELIMINAR / DESACTIVAR CLIENTE
    path(
        "eliminar/<int:cliente_id>/",
        views.eliminar_cliente,
        name="eliminar"
    ),
]
