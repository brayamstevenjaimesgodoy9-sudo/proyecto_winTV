import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.test import RequestFactory

from incidencias import asignacion_views as views


class PruebasHU15(unittest.TestCase):
    """
    Pruebas de HU-15 utilizando simulaciones.
    No se crean ni modifican registros en Oracle.
    """

    def setUp(self):
        self.factory = RequestFactory()

        self.orden = SimpleNamespace(
            pk=2,
            estado="PENDIENTE"
        )

        self.tecnico = SimpleNamespace(
            pk=3
        )

    def crear_request(self, ruta):
        request = self.factory.post(ruta)

        request.user = Mock()
        request.user.is_authenticated = True
        request.user.is_superuser = True

        return request

    def crear_formulario(self):
        formulario = Mock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {
            "orden": self.orden,
            "tecnico": self.tecnico,
            "observaciones": "Prueba HU-15"
        }
        return formulario

    # ==========================================
    # PRUEBA 1: REGISTRAR ASIGNACIÓN
    # ==========================================

    def test_registrar_asignacion_tecnico(self):
        request = self.crear_request(
            "/incidencias/asignar-orden/"
        )
        formulario = self.crear_formulario()

        with (
            patch.object(
                views,
                "AsignacionTecnicoForm",
                return_value=formulario
            ),
            patch.object(
                views.AsignacionTecnico.objects,
                "filter"
            ) as filtro,
            patch.object(
                views.OrdenTrabajo.objects,
                "select_for_update"
            ) as bloqueo,
            patch.object(
                views.AsignacionTecnico.objects,
                "create"
            ) as crear,
            patch.object(
                views.transaction,
                "atomic"
            ),
            patch.object(
                views.messages,
                "success"
            ),
            patch.object(
                views,
                "redirect",
                return_value=Mock(status_code=302)
            ),
        ):
            filtro.return_value.exists.return_value = False
            bloqueo.return_value.get.return_value = self.orden

            respuesta = views.asignar_orden_tecnico(request)

            crear.assert_called_once()

            datos = crear.call_args.kwargs

            self.assertEqual(datos["orden"], self.orden)
            self.assertEqual(datos["tecnico"], self.tecnico)
            self.assertEqual(datos["estado"], "ASIGNADO")
            self.assertEqual(
                datos["observaciones"],
                "Prueba HU-15"
            )

            self.assertEqual(respuesta.status_code, 302)

    # ==========================================
    # PRUEBA 2: IMPEDIR DOS TÉCNICOS ACTIVOS
    # ==========================================

    def test_impedir_dos_tecnicos_en_misma_orden(self):
        request = self.crear_request(
            "/incidencias/asignar-orden/"
        )
        formulario = self.crear_formulario()

        with (
            patch.object(
                views,
                "AsignacionTecnicoForm",
                return_value=formulario
            ),
            patch.object(
                views.AsignacionTecnico.objects,
                "filter"
            ) as filtro,
            patch.object(
                views.AsignacionTecnico.objects,
                "create"
            ) as crear,
            patch.object(
                views,
                "render",
                return_value=Mock(status_code=200)
            ),
        ):
            filtro.return_value.exists.return_value = True

            views.asignar_orden_tecnico(request)

            crear.assert_not_called()

            formulario.add_error.assert_called_with(
                "orden",
                "Esta orden ya tiene un técnico responsable asignado."
            )

    # ==========================================
    # PRUEBA 3: VALIDAR ESTADO EN_PROCESO
    # ==========================================

    def test_impedir_asignacion_si_esta_en_proceso(self):
        request = self.crear_request(
            "/incidencias/asignar-orden/"
        )
        formulario = self.crear_formulario()

        with (
            patch.object(
                views,
                "AsignacionTecnicoForm",
                return_value=formulario
            ),
            patch.object(
                views.AsignacionTecnico.objects,
                "filter"
            ) as filtro,
            patch.object(
                views.AsignacionTecnico.objects,
                "create"
            ) as crear,
            patch.object(
                views,
                "render",
                return_value=Mock(status_code=200)
            ),
        ):
            filtro.return_value.exists.return_value = True

            views.asignar_orden_tecnico(request)

            filtro.assert_any_call(
                orden=self.orden,
                estado__in=["ASIGNADO", "EN_PROCESO"]
            )

            crear.assert_not_called()

    # ==========================================
    # PRUEBA 4: EDITAR ASIGNACIÓN
    # ==========================================

    def test_editar_asignacion_tecnico(self):
        request = self.crear_request(
            "/incidencias/asignacion/1/editar/"
        )

        fecha_original = object()

        asignacion = SimpleNamespace(
            pk=1,
            orden_id=2,
            estado="ASIGNADO",
            tecnico=SimpleNamespace(pk=4),
            observaciones="Observación anterior",
            fecha_asignacion=fecha_original,
            save=Mock()
        )

        formulario = self.crear_formulario()
        operaciones = []

        def obtener_orden(*args, **kwargs):
            operaciones.append("orden")
            return self.orden

        def obtener_asignacion(*args, **kwargs):
            operaciones.append("asignacion")
            return asignacion

        with (
            patch.object(
                views.AsignacionTecnico.objects,
                "select_related"
            ) as consulta,
            patch.object(
                views,
                "EditarAsignacionTecnicoForm",
                return_value=formulario
            ),
            patch.object(
                views.OrdenTrabajo.objects,
                "select_for_update"
            ) as bloqueo_orden,
            patch.object(
                views.AsignacionTecnico.objects,
                "select_for_update"
            ) as bloqueo_asignacion,
            patch.object(
                views.AsignacionTecnico.objects,
                "filter"
            ) as filtro,
            patch.object(
                views.transaction,
                "atomic"
            ),
            patch.object(
                views.messages,
                "success"
            ),
            patch.object(
                views,
                "redirect",
                return_value=Mock(status_code=302)
            ),
        ):
            consulta.return_value.get.return_value = asignacion

            bloqueo_orden.return_value.get.side_effect = (
                obtener_orden
            )

            bloqueo_asignacion.return_value.get.side_effect = (
                obtener_asignacion
            )

            filtro.return_value.exclude.return_value.exists.return_value = False

            respuesta = views.editar_asignacion_tecnico(
                request,
                pk=1
            )

            # Verificar orden de los bloqueos
            self.assertEqual(
                operaciones,
                ["orden", "asignacion"]
            )

            bloqueo_orden.return_value.get.assert_called_once_with(
                pk=2
            )

            bloqueo_asignacion.return_value.get.assert_called_once_with(
                pk=1
            )

            # Verificar técnico actualizado
            self.assertEqual(
                asignacion.tecnico,
                self.tecnico
            )

            # Verificar observaciones actualizadas
            self.assertEqual(
                asignacion.observaciones,
                "Prueba HU-15"
            )

            # Verificar que no cambió el ID
            self.assertEqual(asignacion.pk, 1)

            # Verificar que no cambió la fecha
            self.assertIs(
                asignacion.fecha_asignacion,
                fecha_original
            )

            # Verificar los únicos campos guardados
            asignacion.save.assert_called_once_with(
                update_fields=[
                    "tecnico",
                    "observaciones"
                ]
            )

            self.assertEqual(respuesta.status_code, 302)
