
from django import forms

# HU-18: Transiciones de estado propuestas.
# Los estados finales quedan cerrados.

TRANSICIONES = {
    "PENDIENTE": ("PROGRAMADA", "CANCELADA"),
    "PROGRAMADA": ("EN_PROCESO", "CANCELADA"),
    "EN_PROCESO": ("FINALIZADA", "CANCELADA"),
    "FINALIZADA": (),
    "CANCELADA": (),
}

ETIQUETAS = {
    "PENDIENTE": "Pendiente",
    "PROGRAMADA": "Programada",
    "EN_PROCESO": "En proceso",
    "FINALIZADA": "Finalizada",
    "CANCELADA": "Cancelada",
}


class EstadoOrdenForm(forms.Form):

    estado = forms.ChoiceField(
        label="Nuevo estado",
        choices=[],
        widget=forms.Select(
            attrs={
                "class": "wintv-inc-input",
            }
        ),
    )

    def __init__(
        self,
        *args,
        estado_actual=None,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        disponibles = TRANSICIONES.get(
            estado_actual, ()
        )

        self.fields["estado"].choices = [
            ("", "Seleccione un nuevo estado")
        ] + [
            (estado, ETIQUETAS[estado])
            for estado in disponibles
        ]
