from django import forms
from .models import Contrato, Plan
from clientes.models import Cliente
from . import estados

class ContratoForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = [
            "cliente",
            "plan",
            "fecha_inicio",
            "direccion_instalacion"
        ]
        widgets = {
            "fecha_inicio": forms.DateInput(
                attrs={"type": "date"},
                format="%Y-%m-%d"
            )
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Mostrar planes activos excepto el plan de prueba
        self.fields["plan"].queryset = (
            Plan.objects.filter(activo=1)
            .exclude(nombre__iexact="PLAN PRUEBA 100 MBPS")
        )

        # Mostrar clientes activos
        self.fields["cliente"].queryset = (
            Cliente.objects.filter(activo=1)
        )

class ContratoEditarForm(forms.ModelForm):
    class Meta:
        model = Contrato
        fields = [
            "plan",
            "direccion_instalacion"
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Excluir el plan de prueba del formulario de edición
        self.fields["plan"].queryset = (
            Plan.objects.filter(activo=1)
            .exclude(nombre__iexact="PLAN PRUEBA 100 MBPS")
        )

class CambiarEstadoForm(forms.Form):
    estado = forms.ChoiceField(
        choices=estados.OPCIONES_ESTADO
    )