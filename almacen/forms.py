from django import forms
from .models import Producto


class RegistroProductoForm(forms.ModelForm):
    categoria = forms.ChoiceField(
        choices=[
            ("EQUIPO", "Equipo"),
            ("MATERIAL", "Material"),
        ],
        label="Categoría"
    )

    class Meta:
        model = Producto
        fields = [
            "codigo",
            "nombre",
            "descripcion",
            "categoria",
            "unidad_medida",
        ]

        labels = {
            "codigo": "Código del producto",
            "nombre": "Nombre del producto",
            "descripcion": "Descripción",
            "unidad_medida": "Unidad de medida",
        }

        widgets = {
            "descripcion": forms.Textarea(attrs={"rows": 3}),
        }


class IngresoAlmacenForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=1),
        label="Producto"
    )

    cantidad = forms.IntegerField(
        min_value=1,
        label="Cantidad"
    )

    motivo = forms.CharField(
        max_length=250,
        label="Motivo del ingreso"
    )

    observaciones = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
        label="Observaciones"
    )
