from unittest import TestCase
from unittest.mock import Mock, patch

from django.http import HttpResponse
from django.test import RequestFactory

from incidencias.asignacion_views import asignar_orden_tecnico


class PruebasHU15(TestCase):

    def test_registrar_asignacion_tecnico(self):
        request = RequestFactory().post(
            "/incidencias/asignar-orden/",
            HTTP_HOST="localhost"
        )

        request.user = Mock(
            is_authenticated=True,
            is_superuser=True
        )

        orden = Mock(pk=1, estado="PENDIENTE")
        tecnico = Mock(pk=2)

        formulario = Mock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {
            "orden": orden,
            "tecnico": tecnico,
            "observaciones": "Asignacion de prueba"
        }

        with (
            patch(
                "incidencias.asignacion_views.AsignacionTecnicoForm",
                return_value=formulario
            ),
            patch(
                "incidencias.asignacion_views.AsignacionTecnico.objects.filter"
            ) as filtro,
            patch(
                "incidencias.asignacion_views.OrdenTrabajo.objects.select_for_update"
            ) as bloqueo,
            patch(
                "incidencias.asignacion_views.AsignacionTecnico.objects.create"
            ) as crear,
            patch(
                "incidencias.asignacion_views.transaction.atomic"
            ),
            patch(
                "incidencias.asignacion_views.messages.success"
            ),
        ):
            filtro.return_value.exists.return_value = False
            bloqueo.return_value.get.return_value = orden

            respuesta = asignar_orden_tecnico(request)

            crear.assert_called_once_with(
                orden=orden,
                tecnico=tecnico,
                fecha_asignacion=crear.call_args.kwargs["fecha_asignacion"],
                estado="ASIGNADO",
                observaciones="Asignacion de prueba"
            )

            self.assertEqual(respuesta.status_code, 302)
