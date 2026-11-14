
from django import forms
from almacen.models import OrdenTrabajo


class DiagnosticoOrdenForm(forms.ModelForm):
    class Meta:
        model = OrdenTrabajo

        fields = [
            "diagnostico",
            "solucion",
            "observaciones",
        ]

        labels = {
            "diagnostico": "Diagnóstico de la avería",
            "solucion": "Solución propuesta o aplicada",
            "observaciones": "Observaciones técnicas",
        }

        widgets = {
            "diagnostico": forms.Textarea(attrs={
                "rows": 5,
                "placeholder": "Describe el problema identificado..."
            }),
            "solucion": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe la solución técnica..."
            }),
            "observaciones": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Observaciones adicionales..."
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["diagnostico"].required = True

        for campo in self.fields.values():
            campo.widget.attrs["style"] = (
                "width:100%; padding:12px; "
                "border:1px solid #cbd5e1; "
                "border-radius:8px; "
                "font:inherit; box-sizing:border-box;"
            )
