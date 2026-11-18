
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.http import HttpResponseForbidden

from almacen.models import OrdenTrabajo
from incidencias.models import Incidencia
from servicios.models import Contrato

from .forms import ClienteForm
from .models import Cliente


# ==========================================
# PERMISOS PARA GESTIONAR CLIENTES
# ==========================================

def puede_gestionar_clientes(usuario):
    if not usuario.is_authenticated:
        return False

    return (
        usuario.is_superuser
        or usuario.groups.filter(
            name__in=["ADMINISTRADOR", "VENDEDOR"]
        ).exists()
    )


# ==========================================
# HU-01: REGISTRAR CLIENTES
# ==========================================

@login_required
def registrar_cliente(request):

    if request.method == "POST":
        formulario = ClienteForm(request.POST)

        if formulario.is_valid():
            try:
                with transaction.atomic():
                    formulario.save()

                messages.success(
                    request,
                    "Cliente registrado correctamente."
                )

                return redirect("clientes:registrar")

            except IntegrityError:
                formulario.add_error(
                    None,
                    "No se pudo registrar el cliente. "
                    "Verifique que el documento no esté duplicado."
                )
    else:
        formulario = ClienteForm()

    return render(
        request,
        "clientes/registrar.html",
        {
            "formulario": formulario,
            "modo_edicion": False,
        }
    )


# ==========================================
# HU-06: BUSCAR CLIENTES
# ==========================================

@login_required
def buscar_clientes(request):

    busqueda = request.GET.get("q", "").strip()

    # Mostrar únicamente clientes activos
    clientes = Cliente.objects.filter(activo=1)

    if busqueda:

        filtros = (
            Q(nombres__icontains=busqueda)
            | Q(apellidos__icontains=busqueda)
            | Q(razon_social__icontains=busqueda)
            | Q(numero_documento__icontains=busqueda)
        )

        if busqueda.isdigit():
            filtros |= Q(id_cliente=int(busqueda))

        clientes = clientes.filter(filtros)

    clientes = clientes.order_by("-id_cliente")[:50]

    return render(
        request,
        "clientes/buscar.html",
        {
            "clientes": clientes,
            "busqueda": busqueda,
            "puede_gestionar": puede_gestionar_clientes(
                request.user
            ),
        }
    )


# ==========================================
# HU-04: CONSULTAR HISTORIAL DEL CLIENTE
# RESPONSABLE: JHAMPIER
# ==========================================

@login_required
def historial_cliente(request, cliente_id):

    if not puede_gestionar_clientes(request.user):
        return HttpResponseForbidden(
            "No tienes permisos para consultar "
            "el historial de clientes."
        )

    cliente = get_object_or_404(
        Cliente,
        pk=cliente_id,
    )

    contratos = list(
        Contrato.objects.filter(
            cliente_id=cliente.pk
        )
        .select_related("plan")
        .order_by("-fecha_inicio", "-id_contrato")
    )

    ids_contratos = [
        contrato.pk
        for contrato in contratos
    ]

    incidencias = list(
        Incidencia.objects.filter(
            id_cliente=cliente.pk
        )
        .select_related("tipo_averia")
        .order_by("-fecha_reporte", "-id_incidencia")
    )

    ordenes = list(
        OrdenTrabajo.objects.filter(
            id_contrato__in=ids_contratos
        )
        .order_by("-fecha_creacion", "-id_orden")
    )

    return render(
        request,
        "clientes/historial.html",
        {
            "cliente": cliente,
            "contratos": contratos,
            "incidencias": incidencias,
            "ordenes": ordenes,
        }
    )


# ==========================================
# EDITAR CLIENTE
# ==========================================

@login_required
def editar_cliente(request, cliente_id):

    if not puede_gestionar_clientes(request.user):
        return HttpResponseForbidden(
            "No tienes permisos para editar clientes."
        )

    cliente = get_object_or_404(
        Cliente,
        pk=cliente_id,
        activo=1,
    )

    if request.method == "POST":

        formulario = ClienteForm(
            request.POST,
            instance=cliente,
        )

        if formulario.is_valid():
            try:
                with transaction.atomic():
                    formulario.save()

                messages.success(
                    request,
                    "Cliente actualizado correctamente."
                )

                return redirect("clientes:buscar")

            except IntegrityError:
                formulario.add_error(
                    None,
                    "No se pudieron guardar los cambios. "
                    "Verifique que el documento no esté duplicado."
                )

    else:
        formulario = ClienteForm(instance=cliente)

    return render(
        request,
        "clientes/registrar.html",
        {
            "formulario": formulario,
            "modo_edicion": True,
            "cliente": cliente,
        }
    )


# ==========================================
# ELIMINAR CLIENTE (DESACTIVACIÓN LÓGICA)
# ==========================================

@login_required
def eliminar_cliente(request, cliente_id):

    if not puede_gestionar_clientes(request.user):
        return HttpResponseForbidden(
            "No tienes permisos para eliminar clientes."
        )

    cliente = get_object_or_404(
        Cliente,
        pk=cliente_id,
        activo=1,
    )

    # Nunca eliminar mediante GET
    if request.method == "POST":

        with transaction.atomic():
            cliente.activo = 0
            cliente.save(update_fields=["activo"])

        messages.success(
            request,
            "Cliente desactivado correctamente. "
            "Su información e historial se conservan."
        )

        return redirect("clientes:buscar")

    return render(
        request,
        "clientes/confirmar_eliminar.html",
        {
            "cliente": cliente,
        }
    )
