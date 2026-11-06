
from django.urls import path
from . import views

app_name = 'incidencias'

urlpatterns = [
    path(
        'registrar/',
        views.registrar_incidencia,
        name='registrar'
    ),

    path(
        'listar/',
        views.listar_incidencias,
        name='listar'
    ),
]
