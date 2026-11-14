
from django import forms
from django.contrib.auth import get_user_model
from django.forms import formset_factory
from django.db.models import F

from .models import (
    Producto,
    OrdenTrabajo,
    EquipoCliente,
    DetalleEntrega,
)


# ==========================================
# REGISTRO DE PRODUCTOS
# ==========================================

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


# ==========================================
# INGRESO DE PRODUCTOS AL ALMACÉN
# ==========================================

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


# ==========================================
# CONFIGURACIÓN DE STOCK MÍNIMO
# ==========================================

class ConfigurarStockMinimoForm(forms.Form):
    producto = forms.ModelChoiceField(
        queryset=Producto.objects.filter(
            activo=1
        ).order_by("nombre"),
        label="Producto",
    )

    stock_minimo = forms.IntegerField(
        min_value=0,
        initial=20,
        label="Nuevo stock mínimo",
    )


# ==========================================
# SALIDA DE EQUIPOS Y MATERIALES A TÉCNICOS
# HU-08
# ==========================================

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


# ==========================================
# HU-09: ASOCIAR EQUIPOS ENTREGADOS
# A UN CLIENTE
# RESPONSABLE: JHAMPIER
# ==========================================

class AsignarEquipoClienteForm(forms.ModelForm):

    class Meta:
        model = EquipoCliente

        fields = [
            "cliente",
            "producto",
            "orden",
            "numero_serie",
            "observaciones",
        ]

        labels = {
            "cliente": "Cliente",
            "producto": "Equipo entregado",
            "orden": "Orden de trabajo",
            "numero_serie": "Número de serie",
            "observaciones": "Observaciones",
        }

        widgets = {
            "numero_serie": forms.TextInput(
                attrs={
                    "placeholder": "Ingrese el número de serie",
                }
            ),
            "observaciones": forms.Textarea(
                attrs={"rows": 3}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # HU-09: Textos de selección en español.
        for campo in ("cliente", "producto", "orden"):
            self.fields[campo].empty_label = "Seleccione una opción"

        # Mostrar únicamente clientes activos.
        self.fields["cliente"].queryset = (
            self.fields["cliente"].queryset
            .filter(activo=1)
            .order_by("nombres", "apellidos")
        )

        # Mostrar solamente equipos activos.
        self.fields["producto"].queryset = (
            Producto.objects.filter(
                activo=1,
                categoria="EQUIPO",
            ).order_by("nombre")
        )

        # HU-09: La orden es obligatoria para
        # verificar la entrega previa del equipo.
        self.fields["orden"].required = True

        self.fields["orden"].queryset = (
            OrdenTrabajo.objects.filter(
                estado__in=["PROGRAMADA", "EN_PROCESO"]
            ).order_by("-fecha_creacion")
        )

    def clean(self):
        cleaned_data = super().clean()

        cliente = cleaned_data.get("cliente")
        orden = cleaned_data.get("orden")

        if cliente and orden:
            from servicios.models import Contrato

            pertenece_cliente = Contrato.objects.filter(
                pk=orden.id_contrato,
                cliente=cliente,
            ).exists()

            if not pertenece_cliente:
                self.add_error(
                    "orden",
                    "La orden seleccionada no pertenece "
                    "a un contrato de este cliente."
                )

        return cleaned_data


# ==========================================
# HU-17: REGISTRAR MATERIALES USADOS
# EN REPARACIÓN
# ==========================================

class RegistrarMaterialUtilizadoForm(forms.Form):

    detalle_id = forms.IntegerField(
        min_value=1,
        widget=forms.HiddenInput()
    )

    cantidad = forms.IntegerField(
        min_value=1,
        label="Cantidad utilizada",
        widget=forms.NumberInput(
            attrs={"min": 1}
        )
    )


# HU-11: DEVOLUCIÓN DE MATERIALES

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

class ReporteMovimientosForm(forms.Form):
    fecha_desde = forms.DateField(
        required=False,
        label="Fecha desde",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    fecha_hasta = forms.DateField(
        required=False,
        label="Fecha hasta",
        widget=forms.DateInput(attrs={"type": "date"}),
    )

    tipo_movimiento = forms.ChoiceField(
        required=False,
        label="Tipo de movimiento",
        choices=[
            ("", "Todos los movimientos"),
            ("ENTRADA", "Entradas"),
            ("SALIDA", "Salidas"),
            ("DEVOLUCION", "Devoluciones"),
            ("AJUSTE", "Ajustes"),
        ],
    )

    producto = forms.ModelChoiceField(
        queryset=Producto.objects.all().order_by("nombre"),
        required=False,
        label="Producto",
        empty_label="Todos los productos",
    )

    def clean(self):
        datos = super().clean()

        desde = datos.get("fecha_desde")
        hasta = datos.get("fecha_hasta")

        if desde and hasta and desde > hasta:
            self.add_error(
                "fecha_hasta",
                "La fecha final no puede ser anterior "
                "a la fecha inicial.",
            )

        return datos
