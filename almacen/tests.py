from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .forms import RegistroProductoForm, ConfigurarStockMinimoForm


class StockMinimoFormTests(SimpleTestCase):

    def test_registro_tiene_minimo_predeterminado_20(self):
        form = RegistroProductoForm()
        self.assertEqual(form.fields["stock_minimo"].initial, 20)
        self.assertIn("stock_minimo", form.Meta.fields)

    def test_configuracion_tiene_minimo_predeterminado_20(self):
        form = ConfigurarStockMinimoForm()
        self.assertEqual(form.fields["stock_minimo"].initial, 20)

    def test_rechaza_stock_minimo_negativo(self):
        for clase in (RegistroProductoForm, ConfigurarStockMinimoForm):
            with self.subTest(formulario=clase.__name__):
                campo = clase().fields["stock_minimo"]
                with self.assertRaises(ValidationError):
                    campo.clean(-1)

    def test_permite_stock_minimo_cero(self):
        for clase in (RegistroProductoForm, ConfigurarStockMinimoForm):
            with self.subTest(formulario=clase.__name__):
                campo = clase().fields["stock_minimo"]
                self.assertEqual(campo.clean(0), 0)


class EstadoInventarioTests(SimpleTestCase):

    def test_estados_de_inventario(self):
        escenarios = [
            (25, 20, "Normal"),
            (20, 20, "En el mínimo"),
            (8, 20, "Bajo mínimo"),
            (0, 20, "Agotado"),
            (0, 0, "Agotado"),
        ]

        for actual, minimo, estado in escenarios:
            with self.subTest(actual=actual, minimo=minimo):
                producto = SimpleNamespace(
                    codigo="MAT-PRUEBA",
                    nombre="Producto de prueba",
                    descripcion="Prueba de inventario",
                    categoria="MATERIAL",
                    unidad_medida="UNIDAD",
                    stock_actual=actual,
                    stock_minimo=minimo,
                )

                html = render_to_string(
                    "almacen/inicio.html",
                    {
                        "producto_form": "",
                        "ingreso_form": "",
                        "stock_minimo_form": "",
                        "productos": [producto],
                        "movimientos": [],
                    },
                )

                self.assertIn(
                    ">" + estado + "</span>",
                    html,
                )


from contextlib import nullcontext
from unittest.mock import MagicMock, patch

from django.test import RequestFactory

from .models import Producto, MovimientoAlmacen
from .views import inicio_almacen


class IngresoAtomicoTests(SimpleTestCase):

    def test_ingreso_actualiza_stock_con_f_y_registra_movimiento(self):
        request = RequestFactory().post(
            "/almacen/",
            {"accion": "registrar_ingreso"},
        )

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.id = 7
        usuario.groups.filter.return_value.exists.return_value = True
        request.user = usuario

        producto = SimpleNamespace(pk=41)

        formulario = MagicMock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {
            "producto": producto,
            "cantidad": 5,
            "motivo": "Reposición",
            "observaciones": "",
        }

        with (
            patch("almacen.views.RegistroProductoForm"),
            patch("almacen.views.ConfigurarStockMinimoForm"),
            patch("almacen.views.IngresoAlmacenForm",
                  return_value=formulario),
            patch.object(Producto.objects, "filter") as filtro,
            patch.object(MovimientoAlmacen.objects, "create") as crear,
            patch("almacen.views.transaction.atomic",
                  return_value=nullcontext()) as atomica,
            patch("almacen.views.messages.success"),
        ):
            filtro.return_value.update.return_value = 1

            respuesta = inicio_almacen(request)

            self.assertEqual(respuesta.status_code, 302)

            filtro.assert_called_once_with(
                pk=41,
                activo=1,
            )

            expresion = (
                filtro.return_value.update.call_args
                .kwargs["stock_actual"]
            )

            self.assertEqual(expresion.lhs.name, "stock_actual")
            self.assertEqual(expresion.connector, "+")
            self.assertEqual(expresion.rhs.value, 5)

            atomica.assert_called_once()
            crear.assert_called_once()

            self.assertEqual(
                crear.call_args.kwargs["cantidad"],
                5,
            )
            self.assertEqual(
                crear.call_args.kwargs["tipo_movimiento"],
                "ENTRADA",
            )


from django.db import DatabaseError
from django.http import HttpResponse


class IngresoErroresTests(SimpleTestCase):

    def _simular_ingreso(self, producto_activo=True, error_movimiento=False):
        request = RequestFactory().post(
            "/almacen/",
            {"accion": "registrar_ingreso"},
        )

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.id = 7
        usuario.groups.filter.return_value.exists.return_value = True
        request.user = usuario

        formulario = MagicMock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {
            "producto": SimpleNamespace(pk=41),
            "cantidad": 5,
            "motivo": "Reposición",
            "observaciones": "",
        }

        with (
            patch("almacen.views.RegistroProductoForm"),
            patch("almacen.views.ConfigurarStockMinimoForm"),
            patch(
                "almacen.views.IngresoAlmacenForm",
                return_value=formulario,
            ),
            patch.object(Producto.objects, "filter") as filtro,
            patch.object(MovimientoAlmacen.objects, "create") as crear,
            patch(
                "almacen.views.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "almacen.views.render",
                return_value=HttpResponse("Formulario de almacén"),
            ),
            patch("almacen.views.messages.error") as mensaje_error,
            patch("almacen.views.messages.success") as mensaje_exito,
            patch("almacen.views.logger.exception") as registro_error,
        ):
            filtro.return_value.update.return_value = (
                1 if producto_activo else 0
            )

            if error_movimiento:
                crear.side_effect = DatabaseError(
                    "Error simulado de Oracle"
                )

            respuesta = inicio_almacen(request)

            self.assertEqual(respuesta.status_code, 200)
            mensaje_error.assert_called_once()
            mensaje_exito.assert_not_called()

            return crear, mensaje_error, registro_error

    def test_producto_desactivado_no_registra_movimiento(self):
        crear, mensaje, registro = self._simular_ingreso(
            producto_activo=False
        )

        crear.assert_not_called()
        registro.assert_not_called()

        self.assertIn(
            "ya no está disponible",
            mensaje.call_args.args[1],
        )

    def test_error_al_crear_movimiento_muestra_mensaje(self):
        crear, mensaje, registro = self._simular_ingreso(
            error_movimiento=True
        )

        crear.assert_called_once()
        registro.assert_called_once()

        self.assertIn(
            "error de base de datos",
            mensaje.call_args.args[1],
        )
