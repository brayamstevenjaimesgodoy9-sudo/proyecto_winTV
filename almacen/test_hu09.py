
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.core.exceptions import (
    PermissionDenied,
    ValidationError,
)
from django.test import SimpleTestCase

from .services import registrar_equipo_cliente


class RegistrarEquipoClienteTests(SimpleTestCase):

    def crear_usuario(self, autorizado=True):
        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = autorizado
        return usuario

    def datos_validos(self):
        return {
            "cliente_id": 1,
            "producto_id": 2,
            "orden_id": 3,
            "numero_serie": "ROUTER-001",
            "usuario": self.crear_usuario(),
            "observaciones": "Equipo instalado",
        }

    def test_rechaza_usuario_sin_permisos(self):
        datos = self.datos_validos()
        datos["usuario"] = self.crear_usuario(False)
        datos["usuario"].groups.filter.return_value.exists.return_value = False

        with self.assertRaises(PermissionDenied):
            registrar_equipo_cliente(**datos)

    def test_rechaza_identificadores_invalidos(self):
        for campo in (
            "cliente_id",
            "producto_id",
            "orden_id",
        ):
            with self.subTest(campo=campo):
                datos = self.datos_validos()
                datos[campo] = 0

                with self.assertRaises(ValidationError):
                    registrar_equipo_cliente(**datos)

    def test_rechaza_numero_serie_demasiado_largo(self):
        datos = self.datos_validos()
        datos["numero_serie"] = "X" * 101

        with self.assertRaises(ValidationError):
            registrar_equipo_cliente(**datos)

    def test_rechaza_observaciones_demasiado_largas(self):
        datos = self.datos_validos()
        datos["observaciones"] = "A" * 501

        with self.assertRaises(ValidationError):
            registrar_equipo_cliente(**datos)

    @patch("almacen.services.transaction.atomic")
    @patch("almacen.services.OrdenTrabajo.objects")
    @patch("almacen.services.Cliente.objects")
    @patch("almacen.services.Producto.objects")
    @patch("almacen.services.Contrato.objects")
    @patch("almacen.services.EquipoCliente.objects")
    @patch("almacen.services.DetalleEntrega.objects")
    def test_registra_equipo_sin_descontar_stock(
        self,
        mock_detalles,
        mock_equipos,
        mock_contratos,
        mock_productos,
        mock_clientes,
        mock_ordenes,
        mock_atomic,
    ):
        # Orden válida para realizar la instalación.
        mock_ordenes.select_for_update.return_value.get.return_value = (
            SimpleNamespace(
                id_contrato=5,
                estado="EN_PROCESO",
            )
        )

        mock_clientes.filter.return_value.exists.return_value = True
        mock_productos.filter.return_value.exists.return_value = True
        mock_contratos.filter.return_value.exists.return_value = True
        mock_equipos.filter.return_value.exists.return_value = False

        detalle = SimpleNamespace(
            pk=10,
            cantidad_entregada=3,
            cantidad_utilizada=1,
            cantidad_devuelta=0,
        )

        mock_detalles.select_for_update.return_value.filter.return_value.order_by.return_value = [
            detalle
        ]

        mock_detalles.filter.return_value.update.return_value = 1

        mock_equipos.create.return_value = SimpleNamespace(
            pk=20
        )

        resultado = registrar_equipo_cliente(
            **self.datos_validos()
        )

        self.assertEqual(resultado.pk, 20)

        mock_equipos.create.assert_called_once()

        mock_detalles.filter.return_value.update.assert_called_once()

        # HU-09 no debe volver a descontar el stock.
        mock_productos.filter.return_value.update.assert_not_called()

    @patch("almacen.services.transaction.atomic")
    @patch("almacen.services.OrdenTrabajo.objects")
    @patch("almacen.services.Cliente.objects")
    @patch("almacen.services.Producto.objects")
    @patch("almacen.services.Contrato.objects")
    @patch("almacen.services.EquipoCliente.objects")
    @patch("almacen.services.DetalleEntrega.objects")
    def test_rechaza_equipo_sin_disponibilidad(
        self,
        mock_detalles,
        mock_equipos,
        mock_contratos,
        mock_productos,
        mock_clientes,
        mock_ordenes,
        mock_atomic,
    ):
        # Orden válida para realizar una instalación.
        mock_ordenes.select_for_update.return_value.get.return_value = (
            SimpleNamespace(
                id_contrato=5,
                estado="EN_PROCESO",
            )
        )

        mock_clientes.filter.return_value.exists.return_value = True
        mock_productos.filter.return_value.exists.return_value = True
        mock_contratos.filter.return_value.exists.return_value = True
        mock_equipos.filter.return_value.exists.return_value = False

        detalle = SimpleNamespace(
            pk=10,
            cantidad_entregada=2,
            cantidad_utilizada=2,
            cantidad_devuelta=0,
        )

        mock_detalles.select_for_update.return_value.filter.return_value.order_by.return_value = [
            detalle
        ]

        with self.assertRaises(ValidationError):
            registrar_equipo_cliente(
                **self.datos_validos()
            )

        # No debe registrar una asociación sin disponibilidad.
        mock_equipos.create.assert_not_called()

    @patch("almacen.services.transaction.atomic")
    @patch("almacen.services.OrdenTrabajo.objects")
    @patch("almacen.services.EquipoCliente.objects")
    def test_rechaza_ordenes_en_estados_no_permitidos(
        self,
        mock_equipos,
        mock_ordenes,
        mock_atomic,
    ):
        estados_no_permitidos = [
            "PENDIENTE",
            "FINALIZADA",
            "CANCELADA",
        ]

        for estado in estados_no_permitidos:
            with self.subTest(estado=estado):

                mock_ordenes.select_for_update.return_value.get.return_value = (
                    SimpleNamespace(
                        id_contrato=5,
                        estado=estado,
                    )
                )

                with self.assertRaises(ValidationError):
                    registrar_equipo_cliente(
                        **self.datos_validos()
                    )

        # Ninguna orden inválida debe generar asociaciones.
        mock_equipos.create.assert_not_called()
