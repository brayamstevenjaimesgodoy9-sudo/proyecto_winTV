
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from django.test import RequestFactory, SimpleTestCase
from django.urls import reverse

from .views import historial_cliente


# ==========================================
# HU-04: PRUEBAS DEL HISTORIAL DEL CLIENTE
# RESPONSABLE: JHAMPIER
# ==========================================

class HistorialClienteTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()
        self.url = reverse(
            "clientes:historial",
            args=[3],
        )

    def crear_usuario(self):
        """
        Crea un usuario simulado con permisos
        para consultar el historial.
        """
        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = True
        return usuario

    def crear_cliente(self):
        """
        Crea un cliente simulado para las pruebas.
        """
        return SimpleNamespace(
            pk=3,
            id_cliente=3,
            nombres="Cliente",
            apellidos="Prueba",
            razon_social="",
            activo=1,
        )

    # ==========================================
    # PRUEBA 1: VERIFICAR LA URL
    # ==========================================

    def test_url_historial_cliente(self):
        self.assertEqual(
            self.url,
            "/clientes/historial/3/",
        )

    # ==========================================
    # PRUEBA 2: REQUIERE INICIAR SESIÓN
    # ==========================================

    def test_requiere_iniciar_sesion(self):
        request = self.factory.get(self.url)
        request.user = AnonymousUser()

        respuesta = historial_cliente(
            request,
            cliente_id=3,
        )

        self.assertEqual(
            respuesta.status_code,
            302,
        )

        self.assertIn(
            "/usuarios/login/",
            respuesta["Location"],
        )

    # ==========================================
    # PRUEBA 3: CONSULTAR HISTORIAL DEL CLIENTE
    # ==========================================

    @patch("clientes.views.render")
    @patch("clientes.views.OrdenTrabajo.objects")
    @patch("clientes.views.Incidencia.objects")
    @patch("clientes.views.Contrato.objects")
    @patch("clientes.views.get_object_or_404")
    def test_consulta_historial_del_cliente(
        self,
        mock_cliente,
        mock_contratos,
        mock_incidencias,
        mock_ordenes,
        mock_render,
    ):
        request = self.factory.get(self.url)
        request.user = self.crear_usuario()

        cliente = self.crear_cliente()
        mock_cliente.return_value = cliente

        contrato = SimpleNamespace(
            pk=1,
            id_contrato=1,
        )

        mock_contratos.filter.return_value.select_related.return_value.order_by.return_value = [
            contrato
        ]

        mock_incidencias.filter.return_value.select_related.return_value.order_by.return_value = []

        mock_ordenes.filter.return_value.order_by.return_value = []

        mock_render.return_value.status_code = 200

        respuesta = historial_cliente(
            request,
            cliente_id=3,
        )

        self.assertEqual(
            respuesta.status_code,
            200,
        )

        mock_cliente.assert_called_once()

        mock_contratos.filter.assert_called_once_with(
            cliente_id=3,
        )

        mock_incidencias.filter.assert_called_once_with(
            id_cliente=3,
        )

        mock_ordenes.filter.assert_called_once_with(
            id_contrato__in=[1],
        )

        contexto = mock_render.call_args.args[2]

        self.assertEqual(
            contexto["cliente"],
            cliente,
        )

        self.assertEqual(
            contexto["contratos"],
            [contrato],
        )

        self.assertEqual(
            contexto["incidencias"],
            [],
        )

        self.assertEqual(
            contexto["ordenes"],
            [],
        )

    # ==========================================
    # PRUEBA 4: CLIENTE SIN HISTORIAL
    # ==========================================

    @patch("clientes.views.render")
    @patch("clientes.views.OrdenTrabajo.objects")
    @patch("clientes.views.Incidencia.objects")
    @patch("clientes.views.Contrato.objects")
    @patch("clientes.views.get_object_or_404")
    def test_cliente_sin_historial(
        self,
        mock_cliente,
        mock_contratos,
        mock_incidencias,
        mock_ordenes,
        mock_render,
    ):
        request = self.factory.get(self.url)
        request.user = self.crear_usuario()

        mock_cliente.return_value = self.crear_cliente()

        mock_contratos.filter.return_value.select_related.return_value.order_by.return_value = []

        mock_incidencias.filter.return_value.select_related.return_value.order_by.return_value = []

        mock_ordenes.filter.return_value.order_by.return_value = []

        mock_render.return_value.status_code = 200

        historial_cliente(
            request,
            cliente_id=3,
        )

        contexto = mock_render.call_args.args[2]

        self.assertEqual(
            contexto["contratos"],
            [],
        )

        self.assertEqual(
            contexto["incidencias"],
            [],
        )

        self.assertEqual(
            contexto["ordenes"],
            [],
        )

        mock_ordenes.filter.assert_called_once_with(
            id_contrato__in=[],
        )

    # ==========================================
    # PRUEBA 5: CLIENTE INEXISTENTE
    # ==========================================

    @patch("clientes.views.get_object_or_404")
    def test_cliente_inexistente(
        self,
        mock_cliente,
    ):
        request = self.factory.get(self.url)
        request.user = self.crear_usuario()

        mock_cliente.side_effect = Http404(
            "Cliente no encontrado"
        )

        with self.assertRaises(Http404):
            historial_cliente(
                request,
                cliente_id=999,
            )

    # ==========================================
    # PRUEBA 6: USUARIO SIN PERMISOS
    # ==========================================

    @patch("clientes.views.get_object_or_404")
    def test_rechaza_usuario_sin_permisos(
        self,
        mock_cliente,
    ):
        request = self.factory.get(self.url)

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = False

        usuario.groups.filter.return_value.exists.return_value = False

        request.user = usuario

        respuesta = historial_cliente(
            request,
            cliente_id=3,
        )

        # El sistema debe rechazar la solicitud.
        self.assertEqual(
            respuesta.status_code,
            403,
        )

        # No debe consultar información del cliente.
        mock_cliente.assert_not_called()
