from django import forms
from django.contrib.auth import get_user_model

from almacen.models import OrdenTrabajo

class AsignacionTecnicoForm(forms.Form):
    orden = forms.ModelChoiceField(
        queryset=OrdenTrabajo.objects.none(),
        label="Orden de trabajo"
    )

    tecnico = forms.ModelChoiceField(
        queryset=get_user_model().objects.none(),
        label="Técnico"
    )

    observaciones = forms.CharField(
        label="Observaciones",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["orden"].queryset = OrdenTrabajo.objects.filter(
            estado__in=["PENDIENTE", "PROGRAMADA"]
        ).order_by("id_orden")

        self.fields["tecnico"].queryset = get_user_model().objects.filter(
            is_active=True,
            groups__name="TECNICO"
        ).distinct().order_by("username")

    def clean_observaciones(self):
        observaciones = self.cleaned_data.get("observaciones", "")

        if len(observaciones.encode("utf-8")) > 500:
            raise forms.ValidationError(
                "Las observaciones no pueden superar los 500 bytes."
            )

        return observaciones