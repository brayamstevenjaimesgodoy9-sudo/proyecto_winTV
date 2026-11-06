from functools import wraps

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import UsuarioForm, UsuarioEditarForm


def es_administrador(user):
    return user.groups.filter(name='ADMINISTRADOR').exists()


def solo_administrador(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not es_administrador(request.user):
            return HttpResponseForbidden(
                'Acceso denegado. Solo el ADMINISTRADOR puede gestionar usuarios.'
            )

        return view_func(request, *args, **kwargs)

    return wrapper


@solo_administrador
def crear_usuario(request):
    if request.method == 'POST':
        form = UsuarioForm(request.POST)

        if form.is_valid():
            usuario = form.save(commit=False)

            usuario.set_password(form.cleaned_data['password'])
            usuario.save()

            rol = form.cleaned_data['rol']
            usuario.groups.add(rol)

            messages.success(
                request,
                'Usuario creado correctamente.'
            )

            return redirect('crear_usuario')

    else:
        form = UsuarioForm()

    return render(
        request,
        'usuarios/crear_usuario.html',
        {'form': form}
    )


@solo_administrador
def listar_usuarios(request):
    usuarios = User.objects.prefetch_related(
        'groups'
    ).order_by('username')

    return render(
        request,
        'usuarios/listar_usuarios.html',
        {'usuarios': usuarios}
    )


@solo_administrador
def desactivar_usuario(request, usuario_id):
    usuario = User.objects.get(id=usuario_id)

    usuario.is_active = False
    usuario.save()

    messages.success(
        request,
        'Usuario desactivado correctamente.'
    )

    return redirect('listar_usuarios')


@solo_administrador
def activar_usuario(request, usuario_id):
    usuario = User.objects.get(id=usuario_id)

    usuario.is_active = True
    usuario.save()

    messages.success(
        request,
        'Usuario activado correctamente.'
    )

    return redirect('listar_usuarios')


@solo_administrador
def editar_usuario(request, usuario_id):
    usuario = User.objects.get(id=usuario_id)

    rol_actual = usuario.groups.first()

    if request.method == 'POST':
        form = UsuarioEditarForm(
            request.POST,
            instance=usuario
        )

        if form.is_valid():
            usuario = form.save()

            usuario.groups.clear()

            rol = form.cleaned_data['rol']
            usuario.groups.add(rol)

            messages.success(
                request,
                'Usuario actualizado correctamente.'
            )

            return redirect('listar_usuarios')

    else:
        form = UsuarioEditarForm(
            instance=usuario,
            initial={'rol': rol_actual}
        )

    return render(
        request,
        'usuarios/editar_usuario.html',
        {
            'form': form,
            'usuario': usuario,
        }
    )

def iniciar_sesion(request):
    siguiente = request.POST.get('next') or request.GET.get('next')

    if siguiente in ('None', 'null', ''):
        siguiente = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        usuario = authenticate(
            request,
            username=username,
            password=password
        )

        if usuario is not None:
            login(request, usuario)

            if siguiente and url_has_allowed_host_and_scheme(
                url=siguiente,
                allowed_hosts={request.get_host()},
                require_https=request.is_secure()
            ):
                return HttpResponseRedirect(siguiente)

            if es_administrador(usuario):
                return redirect('listar_usuarios')

            if usuario.groups.filter(name='ALMACEN').exists():
                return redirect('inicio_almacen')

            if usuario.is_superuser or usuario.groups.filter(
                name__in=["VENDEDOR", "CAJA"]
            ).exists():
                return redirect('servicios:contrato_lista')

            return HttpResponseForbidden(
                "Tu usuario no tiene una página de inicio asignada."
            )

        messages.error(
            request,
            'Usuario o contraseña incorrectos.'
        )

    return render(
        request,
        'usuarios/login.html',
        {'next': siguiente}
    )

def cerrar_sesion(request):
    logout(request)

    messages.success(
        request,
        'Sesión cerrada correctamente.'
    )

    return redirect('login')