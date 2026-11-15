
from django.urls import path
from . import views

urlpatterns = [
    # Página principal del almacén
    path(
        "",
        views.inicio_almacen,
        name="inicio_almacen",
    ),

    # HU-09: Asociar equipos entregados a clientes
    path(
        "equipos-clientes/asignar/",
        views.asignar_equipo_cliente,
        name="asignar_equipo_cliente",
    ),
    # HU-17: Registrar materiales usados en reparación
path(
    "materiales-usados/",
    views.registrar_materiales_usados,
    name="registrar_materiales_usados",
),
]
