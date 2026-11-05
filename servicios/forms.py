from django import forms
from .models import Contrato, Plan
from clientes.models import Cliente
from . import estados

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["cliente", "plan", "fecha_inicio", "direccion_instalacion"]
        widgets = {"fecha_inicio": forms.DateInput(attrs={"type":"date"}, format="%Y-%m-%d")}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(activo=1)
        self.fields["cliente"].queryset = Cliente.objects.filter(activo=1)

class ContratoEditarForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = ["plan", "direccion_instalacion"]
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields["plan"].queryset = Plan.objects.filter(activo=1) | Plan.objects.filter(pk=self.instance.plan_id)

class CambiarEstadoForm(forms.Form):
    estado = forms.ChoiceField(choices=estados.OPCIONES_ESTADO)
