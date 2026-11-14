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
