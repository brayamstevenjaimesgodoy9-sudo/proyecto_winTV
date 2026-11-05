from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import HttpResponseForbidden
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from .models import Contrato
from .forms import ContratoForm, ContratoEditarForm, CambiarEstadoForm
from .services import ContratoService
from . import estados

@login_required
def contrato_lista(request):
    if not request.user.is_superuser and not request.user.groups.filter(
        name__in=["ADMINISTRADOR", "VENDEDOR", "CAJA"]
    ).exists():
        return HttpResponseForbidden(
            "No tienes permiso para consultar contratos"
        )

    qs = Contrato.objects.select_related(
        "cliente", "plan"
    ).order_by("-fecha_inicio", "-id_contrato")

    estado = request.GET.get("estado", "")

    if estado in dict(estados.OPCIONES_ESTADO):
        qs = qs.filter(estado=estado)

    return render(
        request,
        "servicios/contrato_lista.html",
        {
            "contratos": qs[:100],
            "opciones_estado": estados.OPCIONES_ESTADO,
            "estado_actual": estado,
        }
    )

@login_required
def contrato_nuevo(request):
    if not request.user.groups.filter(name__in=["ADMINISTRADOR", "VENDEDOR"]).exists() and not request.user.is_superuser:
        return HttpResponseForbidden("No tienes permiso para registrar contratos")
    form=ContratoForm(request.POST or None)
    if request.method=="POST" and form.is_valid():
        try:
            contrato=ContratoService().registrar_contrato(**form.cleaned_data)
            messages.success(request,"Contrato registrado")
            return redirect("servicios:contrato_detalle",pk=contrato.pk)
        except ValidationError as e: form.add_error(None,e)
    return render(request,"servicios/contrato_form.html",{"form":form})

@login_required
def contrato_detalle(request, pk):
    if not request.user.is_superuser and not request.user.groups.filter(
        name__in=["ADMINISTRADOR", "VENDEDOR", "CAJA"]
    ).exists():
        return HttpResponseForbidden(
            "No tienes permiso para consultar los detalles del contrato"
        )

    contrato = get_object_or_404(
        Contrato.objects.select_related("cliente", "plan"),
        pk=pk
    )

    return render(
        request,
        "servicios/contrato_detalle.html",
        {"contrato": contrato}
    )

@login_required
def contrato_editar(request,pk):
    if not request.user.groups.filter(name__in=["ADMINISTRADOR", "VENDEDOR"]).exists() and not request.user.is_superuser:
        return HttpResponseForbidden("No tienes permiso para editar contratos")
    contrato=get_object_or_404(Contrato,pk=pk)
    if contrato.estado==estados.CANCELADO: return redirect("servicios:contrato_detalle",pk=pk)
    form=ContratoEditarForm(request.POST or None,instance=contrato)
    if request.method=="POST" and form.is_valid():
        try:
            ContratoService().actualizar(contrato,**form.cleaned_data)
            messages.success(request,"Contrato actualizado")
            return redirect("servicios:contrato_detalle",pk=pk)
        except ValidationError as e: form.add_error(None,e)
    return render(request,"servicios/contrato_editar.html",{"contrato":contrato,"form":form})

@require_POST
@login_required
def contrato_cambiar_estado(request,pk):
    if not request.user.groups.filter(name="ADMINISTRADOR").exists() and not request.user.is_superuser:
        return HttpResponseForbidden("No tienes permiso para cambiar estados")
    contrato=get_object_or_404(Contrato,pk=pk)
    form=CambiarEstadoForm(request.POST)
    if form.is_valid():
        try: ContratoService().cambiar_estado(contrato,form.cleaned_data["estado"])
        except (ValidationError,ValueError,KeyError) as e: messages.error(request,str(e))
    return redirect("servicios:contrato_detalle",pk=pk)
