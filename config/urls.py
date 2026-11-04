
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    # Página principal de WinTV
    path('', TemplateView.as_view(
        template_name='inicio.html'
    ), name='inicio'),

    # Administración
    path('admin/', admin.site.urls),

    # Gestión de clientes
    path('clientes/', include('clientes.urls')),

    # Gestión de usuarios
    path('usuarios/', include('usuarios.urls')),
]
