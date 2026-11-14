from django import forms
from .models import Producto


class RegistroProductoForm(forms.ModelForm):
    stock_minimo = forms.IntegerField(
        min_value=0,
        initial=20,
        label="Stock mínimo",
        help_text="Valor predeterminado: 20 unidades. Puedes modificarlo.",
    )

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
            "stock_minimo",
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


class ConfigurarStockMinimoForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(activo=1).order_by("nombre"),
        label="Producto",
    )

    stock_minimo = forms.IntegerField(
        min_value=0,
        initial=20,
        label="Nuevo stock mínimo",
    )
