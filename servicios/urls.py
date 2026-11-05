from django.urls import path
from . import views
app_name="servicios"
urlpatterns=[
 path("contratos/",views.contrato_lista,name="contrato_lista"),
 path("contratos/nuevo/",views.contrato_nuevo,name="contrato_nuevo"),
 path("contratos/<int:pk>/",views.contrato_detalle,name="contrato_detalle"),
 path("contratos/<int:pk>/editar/",views.contrato_editar,name="contrato_editar"),
 path("contratos/<int:pk>/estado/",views.contrato_cambiar_estado,name="contrato_cambiar_estado"),
]
