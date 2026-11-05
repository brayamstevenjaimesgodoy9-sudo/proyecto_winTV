from django.urls import path
from . import views

urlpatterns = [
    path("", views.inicio_almacen, name="inicio_almacen"),
]