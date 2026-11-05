from django import forms
from .models import Producto


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
        widget=forms.Textarea,
        label="Observaciones"
    )