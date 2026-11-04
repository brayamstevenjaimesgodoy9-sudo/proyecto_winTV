
from django.urls import path
from . import views

app_name = "clientes"

urlpatterns = [
    # HU-01: Registrar clientes
    path(
        "registrar/",
        views.registrar_cliente,
        name="registrar"
    ),

    # HU-06: Buscar clientes
    path(
        "buscar/",
        views.buscar_clientes,
        name="buscar"
    ),
]
