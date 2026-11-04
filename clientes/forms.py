
from django import forms
from .models import Cliente


class ClienteForm(forms.ModelForm):

    TIPO_DOCUMENTO = [
        ("", "Seleccione documento"),
        ("DNI", "DNI"),
        ("RUC", "RUC"),
        ("CE", "Carné de extranjería"),
    ]

    tipo_documento = forms.ChoiceField(
        choices=TIPO_DOCUMENTO,
        label="Tipo de documento",
    )

    class Meta:
        model = Cliente

        fields = [
            "tipo_documento",
            "numero_documento",
            "nombres",
            "apellidos",
            "razon_social",
            "direccion",
            "zona",
            "telefono",
            "correo",
        ]

        labels = {
            "numero_documento": "Número de documento",
            "nombres": "Nombres",
            "apellidos": "Apellidos",
            "razon_social": "Razón social",
            "direccion": "Dirección",
            "zona": "Zona",
            "telefono": "Teléfono",
            "correo": "Correo electrónico",
        }

        widgets = {
            "numero_documento": forms.TextInput(
                attrs={
                    "placeholder": "Número de documento",
                    "maxlength": "20",
                }
            ),
            "nombres": forms.TextInput(
                attrs={"placeholder": "Nombres"}
            ),
            "apellidos": forms.TextInput(
                attrs={"placeholder": "Apellidos"}
            ),
            "razon_social": forms.TextInput(
                attrs={"placeholder": "Razón social"}
            ),
            "direccion": forms.TextInput(
                attrs={"placeholder": "Dirección del cliente"}
            ),
            "zona": forms.TextInput(
                attrs={"placeholder": "Zona del cliente"}
            ),
            "telefono": forms.TextInput(
                attrs={"placeholder": "Teléfono (opcional)"}
            ),
            "correo": forms.EmailInput(
                attrs={"placeholder": "Correo (opcional)"}
            ),
        }

    def clean(self):
        datos = super().clean()

        tipo = datos.get("tipo_documento")
        numero = (datos.get("numero_documento") or "").strip()

        nombres = (datos.get("nombres") or "").strip()
        apellidos = (datos.get("apellidos") or "").strip()
        razon_social = (
            datos.get("razon_social") or ""
        ).strip()

        datos["numero_documento"] = numero
        datos["nombres"] = nombres
        datos["apellidos"] = apellidos
        datos["razon_social"] = razon_social

        # Validación del DNI
        if tipo == "DNI":
            if numero and (
                len(numero) != 8 or not numero.isdigit()
            ):
                self.add_error(
                    "numero_documento",
                    "El DNI debe contener exactamente 8 números."
                )

        # Validación del RUC
        elif tipo == "RUC":
            if numero and (
                len(numero) != 11 or not numero.isdigit()
            ):
                self.add_error(
                    "numero_documento",
                    "El RUC debe contener exactamente 11 números."
                )

        # Validación del carné de extranjería
        elif tipo == "CE":
            if numero and not numero.isalnum():
                self.add_error(
                    "numero_documento",
                    "El carné debe contener letras o números."
                )

        # Datos según el tipo de documento
        if tipo == "RUC":
            if not razon_social:
                self.add_error(
                    "razon_social",
                    "Ingrese la razón social de la empresa."
                )

            datos["nombres"] = ""
            datos["apellidos"] = ""

        elif tipo in ("DNI", "CE"):
            if not nombres:
                self.add_error(
                    "nombres",
                    "Ingrese los nombres del cliente."
                )

            if not apellidos:
                self.add_error(
                    "apellidos",
                    "Ingrese los apellidos del cliente."
                )

            datos["razon_social"] = ""

        # Evitar documentos duplicados
        if tipo and numero:
            existentes = Cliente.objects.filter(
                tipo_documento=tipo,
                numero_documento=numero,
            )

            if self.instance.pk:
                existentes = existentes.exclude(
                    pk=self.instance.pk
                )

            if existentes.exists():
                self.add_error(
                    "numero_documento",
                    "Ya existe un cliente registrado con este documento."
                )

        return datos
