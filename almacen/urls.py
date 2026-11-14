from django.urls import path
from . import views
from . import reportes_views

urlpatterns = [
    path("", views.inicio_almacen, name="inicio_almacen"),
    path("reportes/", reportes_views.reporte_movimientos, name="reporte_movimientos"),
]