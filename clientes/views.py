
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q

from .forms import ClienteForm
from .models import Cliente


# HU-01: REGISTRAR CLIENTES
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
            "formulario": formulario
        }
    )


# HU-06: BUSCAR CLIENTES
@login_required
def buscar_clientes(request):

    busqueda = request.GET.get("q", "").strip()

    # Mostrar solamente los clientes activos
    clientes = Cliente.objects.filter(activo=1)

    if busqueda:

        filtros = (
            Q(nombres__icontains=busqueda)
            | Q(apellidos__icontains=busqueda)
            | Q(razon_social__icontains=busqueda)
            | Q(numero_documento__icontains=busqueda)
        )

        # Permitir buscar también por código
        if busqueda.isdigit():
            filtros |= Q(id_cliente=int(busqueda))

        clientes = clientes.filter(filtros)

    # Ordenar del más reciente al más antiguo
    clientes = clientes.order_by("-id_cliente")[:50]

    return render(
        request,
        "clientes/buscar.html",
        {
            "clientes": clientes,
            "busqueda": busqueda,
        }
    )

