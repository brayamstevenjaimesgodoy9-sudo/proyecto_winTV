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


class PermisosAlmacenTests(SimpleTestCase):

    def _crear_peticion(self, superusuario=False, roles=()):
        request = RequestFactory().get("/almacen/")

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = superusuario

        usuario.groups.filter.side_effect = lambda **kwargs: (
            SimpleNamespace(
                exists=lambda: kwargs.get("name") in roles
            )
        )

        request.user = usuario
        return request

    def _ejecutar_vista(self, request):
        with (
            patch("almacen.views.RegistroProductoForm"),
            patch("almacen.views.IngresoAlmacenForm"),
            patch("almacen.views.ConfigurarStockMinimoForm"),
            patch(
                "almacen.views.render",
                return_value=HttpResponse("Almacén autorizado"),
            ),
        ):
            return inicio_almacen(request)

    def test_superusuario_puede_acceder(self):
        request = self._crear_peticion(superusuario=True)
        respuesta = self._ejecutar_vista(request)
        self.assertEqual(respuesta.status_code, 200)

    def test_administrador_puede_acceder(self):
        request = self._crear_peticion(
            roles=("ADMINISTRADOR",)
        )
        respuesta = self._ejecutar_vista(request)
        self.assertEqual(respuesta.status_code, 200)

    def test_almacen_puede_acceder(self):
        request = self._crear_peticion(
            roles=("ALMACEN",)
        )
        respuesta = self._ejecutar_vista(request)
        self.assertEqual(respuesta.status_code, 200)

    def test_usuario_sin_permisos_recibe_403(self):
        request = self._crear_peticion()
        respuesta = self._ejecutar_vista(request)
        self.assertEqual(respuesta.status_code, 403)


from django.core.exceptions import PermissionDenied
from .services import registrar_salida_materiales


class SalidaMaterialesValidacionTests(SimpleTestCase):

    def _usuario_autorizado(self):
        return SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            pk=1,
        )

    def test_rechaza_usuario_no_autenticado(self):
        usuario = SimpleNamespace(is_authenticated=False)

        with self.assertRaises(PermissionDenied):
            registrar_salida_materiales(
                orden_id=1,
                tecnico_id=2,
                detalles=[{"producto_id": 1, "cantidad": 2}],
                usuario=usuario,
            )

    def test_rechaza_usuario_sin_permisos(self):
        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = False
        usuario.groups.filter.return_value.exists.return_value = False

        with self.assertRaises(PermissionDenied):
            registrar_salida_materiales(
                orden_id=1,
                tecnico_id=2,
                detalles=[{"producto_id": 1, "cantidad": 2}],
                usuario=usuario,
            )

    def test_rechaza_cantidad_negativa(self):
        with self.assertRaisesMessage(
            ValidationError, "entero positivo"
        ):
            registrar_salida_materiales(
                orden_id=1,
                tecnico_id=2,
                detalles=[{"producto_id": 1, "cantidad": -5}],
                usuario=self._usuario_autorizado(),
            )

    def test_rechaza_productos_repetidos(self):
        with self.assertRaisesMessage(
            ValidationError, "repetir un producto"
        ):
            registrar_salida_materiales(
                orden_id=1,
                tecnico_id=2,
                detalles=[
                    {"producto_id": 1, "cantidad": 2},
                    {"producto_id": 1, "cantidad": 3},
                ],
                usuario=self._usuario_autorizado(),
            )

    def test_rechaza_observaciones_multibyte(self):
        with self.assertRaisesMessage(
            ValidationError, "500 bytes"
        ):
            registrar_salida_materiales(
                orden_id=1,
                tecnico_id=2,
                detalles=[{"producto_id": 1, "cantidad": 2}],
                usuario=self._usuario_autorizado(),
                observaciones="á" * 300,
            )

    def test_rechaza_observaciones_demasiado_largas(self):
        with self.assertRaisesMessage(
            ValidationError, "500 bytes"
        ):
            registrar_salida_materiales(
                orden_id=1,
                tecnico_id=2,
                detalles=[{"producto_id": 1, "cantidad": 2}],
                usuario=self._usuario_autorizado(),
                observaciones="X" * 501,
            )


from contextlib import ExitStack
from .models import AsignacionTecnico


class SalidaMaterialesFlujoTests(SimpleTestCase):

    def setUp(self):
        self.contexto = ExitStack()
        self.addCleanup(self.contexto.close)

        def simular(ruta, **opciones):
            return self.contexto.enter_context(
                patch(ruta, **opciones)
            )

        simular(
            "almacen.services.transaction.atomic",
            return_value=nullcontext(),
        )

        self.orden = simular(
            "almacen.services.OrdenTrabajo.objects.select_for_update"
        )
        self.orden.return_value.get.return_value.estado = "PROGRAMADA"

        self.asignacion = simular(
            "almacen.services.AsignacionTecnico.objects.select_for_update"
        )
        self.asignacion.return_value.get.return_value.estado = "ASIGNADO"

        usuarios = simular("almacen.services.get_user_model")
        usuarios.return_value.objects.filter.return_value.exists.return_value = True

        self.crear_entrega = simular(
            "almacen.services.EntregaMaterial.objects.create"
        )
        self.crear_entrega.return_value = SimpleNamespace(pk=55)

        self.productos = simular(
            "almacen.services.Producto.objects.filter"
        )
        self.productos.return_value.update.return_value = 1

        self.crear_detalle = simular(
            "almacen.services.DetalleEntrega.objects.create"
        )
        self.crear_movimiento = simular(
            "almacen.services.MovimientoAlmacen.objects.create"
        )

        self.usuario = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            pk=7,
        )

    def registrar(self):
        return registrar_salida_materiales(
            orden_id=12,
            tecnico_id=8,
            detalles=[{"producto_id": 3, "cantidad": 2}],
            usuario=self.usuario,
        )

    def test_entrega_correcta(self):
        entrega = self.registrar()

        self.assertEqual(entrega.pk, 55)
        self.crear_entrega.assert_called_once()
        self.crear_detalle.assert_called_once()
        self.crear_movimiento.assert_called_once()

        self.productos.assert_called_once_with(
            pk=3,
            activo=1,
            stock_actual__gte=2,
        )

        expresion = self.productos.return_value.update.call_args.kwargs[
            "stock_actual"
        ]
        self.assertEqual(expresion.lhs.name, "stock_actual")
        self.assertEqual(expresion.connector, "-")
        self.assertEqual(expresion.rhs.value, 2)

        movimiento = self.crear_movimiento.call_args.kwargs
        self.assertEqual(movimiento["tipo_movimiento"], "SALIDA")
        self.assertEqual(movimiento["cantidad"], 2)
        self.assertEqual(movimiento["id_usuario"], 7)

    def test_stock_insuficiente(self):
        self.productos.return_value.update.return_value = 0

        with self.assertRaisesMessage(
            ValidationError, "Stock insuficiente"
        ):
            self.registrar()

        self.crear_detalle.assert_not_called()
        self.crear_movimiento.assert_not_called()

    def test_orden_cancelada(self):
        self.orden.return_value.get.return_value.estado = "CANCELADA"

        with self.assertRaisesMessage(
            ValidationError, "no permite entregas"
        ):
            self.registrar()

        self.crear_entrega.assert_not_called()

    def test_tecnico_no_asignado(self):
        self.asignacion.return_value.get.side_effect = (
            AsignacionTecnico.DoesNotExist
        )

        with self.assertRaisesMessage(
            ValidationError, "no está asignado"
        ):
            self.registrar()

        self.crear_entrega.assert_not_called()


from django.http import HttpResponse
from django.test import RequestFactory
from django.urls import reverse

from almacen.views import inicio_almacen


class SalidaMaterialesVistaTests(SimpleTestCase):

    def setUp(self):
        self.contexto = ExitStack()
        self.addCleanup(self.contexto.close)

        def simular(ruta, **opciones):
            return self.contexto.enter_context(
                patch(ruta, **opciones)
            )

        self.renderizar = simular(
            "almacen.views.render",
            return_value=HttpResponse("Vista simulada"),
        )

        simular("almacen.views.messages.success")
        simular("almacen.views.Producto.objects.filter")
        simular("almacen.views.MovimientoAlmacen.objects.select_related")

        formulario = simular("almacen.views.SalidaMaterialesForm")
        self.formulario = formulario.return_value
        self.formulario.is_valid.return_value = True
        self.formulario.cleaned_data = {
            "orden": SimpleNamespace(pk=12),
            "tecnico": SimpleNamespace(pk=8),
            "observaciones": "Entrega de prueba",
        }

        formulario_detalles = simular(
            "almacen.views.DetalleSalidaFormSet"
        )
        self.detalles = formulario_detalles.return_value
        self.detalles.is_valid.return_value = True
        self.detalles.cleaned_data = [
            {
                "producto": SimpleNamespace(pk=3),
                "cantidad": 2,
            }
        ]

        self.servicio = simular(
            "almacen.views.registrar_salida_materiales",
            return_value=SimpleNamespace(pk=55),
        )

    def solicitud(self):
        request = RequestFactory().post(
            "/almacen/",
            {"accion": "registrar_salida"},
        )
        request.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            pk=7,
        )
        return request

    def test_salida_valida_invoca_servicio(self):
        respuesta = inicio_almacen(self.solicitud())

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(
            respuesta.url,
            reverse("inicio_almacen"),
        )
        self.servicio.assert_called_once_with(
            orden_id=12,
            tecnico_id=8,
            detalles=[
                {"producto_id": 3, "cantidad": 2}
            ],
            usuario=self.servicio.call_args.kwargs["usuario"],
            observaciones="Entrega de prueba",
        )

    def test_formulario_invalido_no_registra_salida(self):
        self.detalles.is_valid.return_value = False

        respuesta = inicio_almacen(self.solicitud())

        self.assertEqual(respuesta.status_code, 200)
        self.servicio.assert_not_called()
        self.renderizar.assert_called_once()

    def test_error_de_validacion_se_muestra(self):
        self.servicio.side_effect = ValidationError(
            "Stock insuficiente."
        )

        respuesta = inicio_almacen(self.solicitud())

        self.assertEqual(respuesta.status_code, 200)
        self.formulario.add_error.assert_called_once()
        self.servicio.assert_called_once()
