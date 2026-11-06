from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path('', TemplateView.as_view(template_name='inicio.html'), name='inicio'),
    path('admin/', admin.site.urls),
    path('clientes/', include('clientes.urls')),
    path('usuarios/', include('usuarios.urls')),
    path('almacen/', include('almacen.urls')),
    path('servicios/', include('servicios.urls')),
    path('incidencias/', include('incidencias.urls')),
]