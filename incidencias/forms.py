
from clientes.models import Cliente
from servicios.models import Contrato
from django import forms
from .models import Incidencia, TipoAveria


class IncidenciaForm(forms.ModelForm):

    tipo_averia = forms.ModelChoiceField(
        queryset=TipoAveria.objects.filter(activo=1),
        empty_label="Seleccione un tipo de avería",
        label="Tipo de avería"
    )

    class Meta:
        model = Incidencia

        fields = [
            'id_cliente',
            'id_contrato',
            'tipo_averia',
            'descripcion',
            'canal_reporte',
            'ubicacion',
            'prioridad',
        ]

        labels = {
            'id_cliente': 'Código del cliente',
            'id_contrato': 'Código del contrato',
            'descripcion': 'Descripción del problema',
            'canal_reporte': 'Canal de reporte',
            'ubicacion': 'Ubicación de la avería',
            'prioridad': 'Prioridad',
        }

        widgets = {
            'id_cliente': forms.NumberInput(attrs={
                'placeholder': 'Ingrese el código del cliente',
                'min': 1,
            }),

            'id_contrato': forms.NumberInput(attrs={
                'placeholder': 'Ingrese el código del contrato',
                'min': 1,
            }),

            'descripcion': forms.Textarea(attrs={
                'placeholder': 'Describa el problema reportado',
                'rows': 4,
                'maxlength': 500,
            }),

            'canal_reporte': forms.TextInput(attrs={
                'placeholder': 'Ejemplo: Teléfono',
                'maxlength': 30,
            }),

            'ubicacion': forms.TextInput(attrs={
                'placeholder': 'Dirección donde ocurre la avería',
                'maxlength': 200,
            }),

        }


    def clean_id_cliente(self):
        valor = self.cleaned_data['id_cliente']

        if not Cliente.objects.filter(
            pk=valor, activo=1
        ).exists():
            raise forms.ValidationError(
                "El cliente no existe o está inactivo."
            )

        return valor

    def clean_id_contrato(self):
        valor = self.cleaned_data['id_contrato']
        cliente_id = self.cleaned_data.get('id_cliente')

        if cliente_id is not None:
            if not Contrato.objects.filter(
                pk=valor,
                cliente_id=cliente_id
            ).exists():
                raise forms.ValidationError(
                    "El contrato no pertenece al cliente indicado."
                )

        return valor