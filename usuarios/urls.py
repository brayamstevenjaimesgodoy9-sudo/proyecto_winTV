from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.iniciar_sesion, name='login'),
    path('logout/', views.cerrar_sesion, name='logout'),

    path('crear/', views.crear_usuario, name='crear_usuario'),
    path('listar/', views.listar_usuarios, name='listar_usuarios'),

    path(
        'editar/<int:usuario_id>/',
        views.editar_usuario,
        name='editar_usuario'
    ),

    path(
        'desactivar/<int:usuario_id>/',
        views.desactivar_usuario,
        name='desactivar_usuario'
    ),

    path(
        'activar/<int:usuario_id>/',
        views.activar_usuario,
        name='activar_usuario'
    ),
]