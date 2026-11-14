from django import forms
from django.contrib.auth import get_user_model
from django.forms import formset_factory
from django.db.models import F
from .models import Producto, DetalleEntrega


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



from .models import OrdenTrabajo


class SalidaMaterialesForm(forms.Form):
    orden = forms.ModelChoiceField(
        queryset=OrdenTrabajo.objects.filter(
            estado__in=["PROGRAMADA", "EN_PROCESO"]
        ).order_by("-fecha_creacion"),
        label="Orden de trabajo",
        empty_label="Seleccione una orden",
    )

    tecnico = forms.ModelChoiceField(
        queryset=get_user_model().objects.filter(
            is_active=True,
            groups__name="TECNICO",
        ).distinct().order_by("username"),
        label="Técnico responsable",
        empty_label="Seleccione un técnico",
    )

    observaciones = forms.CharField(
        max_length=500,
        required=False,
        label="Observaciones",
        widget=forms.Textarea(attrs={"rows": 3}),
    )


class DetalleSalidaForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(
            activo=1,
            stock_actual__gt=0,
        ).order_by("nombre"),
        label="Equipo o material",
        empty_label="Seleccione un producto",
    )

    cantidad = forms.IntegerField(
        min_value=1,
        max_value=9999999999,
        label="Cantidad a entregar",
    )


DetalleSalidaFormSet = formset_factory(
    DetalleSalidaForm,
    extra=3,
    min_num=1,
    validate_min=True,
    max_num=10,
    validate_max=True,
)

class DetalleDevolucionField(forms.ModelChoiceField):
    def label_from_instance(self, detalle):
        pendiente = (
            detalle.cantidad_entregada
            - detalle.cantidad_utilizada
            - detalle.cantidad_devuelta
        )
        return (
            f"Entrega #{detalle.entrega_id} | "
            f"{detalle.producto.codigo} - {detalle.producto.nombre} | "
            f"Pendiente: {pendiente}"
        )


class DevolucionMaterialForm(forms.Form):
    detalle = DetalleDevolucionField(
        queryset=DetalleEntrega.objects.none(),
        label="Material entregado",
        empty_label="Seleccione un material pendiente",
    )

    cantidad = forms.IntegerField(
        min_value=1,
        max_value=9999999999,
        label="Cantidad a devolver",
    )

    observaciones = forms.CharField(
        required=False,
        max_length=500,
        label="Observaciones",
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["detalle"].queryset = (
            DetalleEntrega.objects
            .filter(
                entrega__estado__in=["ENTREGADA", "PARCIAL"]
            )
            .annotate(
                pendiente=(
                    F("cantidad_entregada")
                    - F("cantidad_utilizada")
                    - F("cantidad_devuelta")
                )
            )
            .filter(pendiente__gt=0)
            .select_related("producto")
            .order_by("-entrega__fecha_entrega", "pk")
        )

    def clean(self):
        datos = super().clean()
        detalle = datos.get("detalle")
        cantidad = datos.get("cantidad")

        if detalle is not None and cantidad is not None:
            if cantidad > detalle.pendiente:
                self.add_error(
                    "cantidad",
                    "La cantidad supera las unidades "
                    "pendientes de devolución.",
                )

        return datos
