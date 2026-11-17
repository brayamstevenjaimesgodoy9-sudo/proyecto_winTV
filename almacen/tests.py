from types import SimpleNamespace

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.test import SimpleTestCase

from .forms import RegistroProductoForm, ConfigurarStockMinimoForm
from .forms import RegistrarMaterialUtilizadoForm

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


# ==========================================
# HU-17: PRUEBAS AUTOMATIZADAS
# RESPONSABLE: BRAYAM
# ==========================================

class RegistrarMaterialUtilizadoFormTests(SimpleTestCase):

    def test_acepta_cantidad_valida(self):
        form = RegistrarMaterialUtilizadoForm(
            data={
                "detalle_id": 1,
                "cantidad": 2,
            }
        )

        self.assertTrue(form.is_valid())

    def test_rechaza_cantidad_cero(self):
        form = RegistrarMaterialUtilizadoForm(
            data={
                "detalle_id": 1,
                "cantidad": 0,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)

    def test_rechaza_cantidad_negativa(self):
        form = RegistrarMaterialUtilizadoForm(
            data={
                "detalle_id": 1,
                "cantidad": -5,
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)


# ==========================================
# HU-17: PRUEBAS DEL SERVICIO
# RESPONSABLE: BRAYAM
# ==========================================

from almacen.materiales_usados_services import registrar_material_utilizado


class RegistrarMaterialUtilizadoServicioTests(SimpleTestCase):

    def test_rechaza_usuario_no_autenticado(self):
        usuario = SimpleNamespace(
            is_authenticated=False,
            is_superuser=False,
        )

        with self.assertRaises(PermissionDenied):
            registrar_material_utilizado(
                detalle_id=1,
                cantidad=1,
                usuario=usuario,
            )

    def test_rechaza_usuario_sin_permisos(self):
        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = False
        usuario.groups.filter.return_value.exists.return_value = False

        with self.assertRaises(PermissionDenied):
            registrar_material_utilizado(
                detalle_id=1,
                cantidad=1,
                usuario=usuario,
            )

    def test_rechaza_cantidad_cero(self):
        usuario = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
        )

        with self.assertRaises(ValidationError):
            registrar_material_utilizado(
                detalle_id=1,
                cantidad=0,
                usuario=usuario,
            )

    def test_rechaza_cantidad_negativa(self):
        usuario = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
        )

        with self.assertRaises(ValidationError):
            registrar_material_utilizado(
                detalle_id=1,
                cantidad=-5,
                usuario=usuario,
            )

    def test_rechaza_asignacion_no_vigente(self):
        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = False
        usuario.pk = 7

        usuario.groups.filter.return_value.exists.side_effect = [
            True,
            False,
            False,
        ]

        detalle = SimpleNamespace(
            pk=1,
            entrega=SimpleNamespace(
                orden_id=1,
                tecnico_id=7,
                estado="ENTREGADA",
            ),
            producto=SimpleNamespace(
                categoria="MATERIAL",
            ),
        )

        orden = SimpleNamespace(
            pk=1,
            estado="PROGRAMADA",
            tipo_orden="REPARACION",
        )

        with (
            patch(
                "almacen.materiales_usados_services.transaction.atomic",
                return_value=nullcontext(),
            ),
            patch(
                "almacen.materiales_usados_services.DetalleEntrega.objects.select_related"
            ) as consulta_detalle,
            patch(
                "almacen.materiales_usados_services.OrdenTrabajo.objects.select_for_update"
            ) as consulta_orden,
            patch(
                "almacen.materiales_usados_services.AsignacionTecnico.objects.filter"
            ) as consulta_asignacion,
        ):
            consulta_detalle.return_value.get.return_value = detalle
            consulta_orden.return_value.get.return_value = orden
            consulta_asignacion.return_value.exists.return_value = False

            with self.assertRaises(PermissionDenied):
                registrar_material_utilizado(
                    detalle_id=1,
                    cantidad=1,
                    usuario=usuario,
                )


# ==========================================
# HU-17: PRUEBAS AUTOMATIZADAS DE REGISTRO
# RESPONSABLE: BRAYAM
# ==========================================

class RegistrarMaterialUtilizadoRegistroTests(SimpleTestCase):

    def setUp(self):
        self.usuario = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
            pk=1,
        )

        self.detalle = SimpleNamespace(
            pk=1,
            cantidad_entregada=10,
            cantidad_utilizada=6,
            cantidad_devuelta=0,
            entrega=SimpleNamespace(
                orden_id=1,
                estado="ENTREGADA",
                tecnico_id=2,
            ),
            producto=SimpleNamespace(
                categoria="MATERIAL",
            ),
        )

        self.orden = SimpleNamespace(
            pk=1,
            estado="PROGRAMADA",
            tipo_orden="REPARACION",
        )

        self.contexto = ExitStack()
        self.addCleanup(self.contexto.close)

        def simular(ruta, **opciones):
            return self.contexto.enter_context(
                patch(ruta, **opciones)
            )

        simular(
            "almacen.materiales_usados_services.transaction.atomic",
            return_value=nullcontext(),
        )

        consulta_detalle = simular(
            "almacen.materiales_usados_services."
            "DetalleEntrega.objects.select_related"
        )
        consulta_detalle.return_value.get.return_value = self.detalle

        consulta_orden = simular(
            "almacen.materiales_usados_services."
            "OrdenTrabajo.objects.select_for_update"
        )
        consulta_orden.return_value.get.return_value = self.orden

        self.filtro = simular(
            "almacen.materiales_usados_services."
            "DetalleEntrega.objects.filter"
        )

        self.detalle.refresh_from_db = MagicMock()

    def test_registro_correcto(self):
        self.filtro.return_value.update.return_value = 1

        resultado = registrar_material_utilizado(
            detalle_id=1,
            cantidad=2,
            usuario=self.usuario,
        )

        self.assertIs(resultado, self.detalle)
        self.filtro.return_value.update.assert_called_once()
        self.detalle.refresh_from_db.assert_called_once()

        expresion = (
            self.filtro.return_value.update.call_args
            .kwargs["cantidad_utilizada"]
        )

        self.assertEqual(expresion.lhs.name, "cantidad_utilizada")
        self.assertEqual(expresion.connector, "+")
        self.assertEqual(expresion.rhs.value, 2)

    def test_rechaza_cantidad_excesiva(self):
        self.filtro.return_value.update.return_value = 0

        with self.assertRaisesMessage(
            ValidationError,
            "La cantidad supera los materiales disponibles."
        ):
            registrar_material_utilizado(
                detalle_id=1,
                cantidad=5,
                usuario=self.usuario,
            )

        self.detalle.refresh_from_db.assert_not_called()

    def test_no_descuenta_stock_nuevamente(self):
        self.filtro.return_value.update.return_value = 1

        registrar_material_utilizado(
            detalle_id=1,
            cantidad=2,
            usuario=self.usuario,
        )

        argumentos = self.filtro.return_value.update.call_args.kwargs

        self.assertEqual(
            list(argumentos.keys()),
            ["cantidad_utilizada"],
        )

        self.assertNotIn("stock_actual", argumentos)

# HU-11: PRUEBAS DE DEVOLUCIONES

from .models import DetalleEntrega
from .services import registrar_devolucion_materiales

class DevolucionMaterialesTests(SimpleTestCase):

    def setUp(self):
        self.contexto = ExitStack()
        self.addCleanup(self.contexto.close)

        def simular(ruta):
            return self.contexto.enter_context(patch(ruta))

        simular(
            "almacen.services.transaction.atomic"
        ).return_value = nullcontext()

        self.entregas = simular(
            "almacen.services.EntregaMaterial.objects.select_for_update"
        )
        self.entregas.return_value.get.return_value = SimpleNamespace(
            pk=4, estado="ENTREGADA"
        )

        self.detalles = simular(
            "almacen.services.DetalleEntrega.objects.select_for_update"
        )
        self.detalles.return_value.get.return_value = SimpleNamespace(
            producto_id=3,
            cantidad_entregada=8,
            cantidad_utilizada=2,
            cantidad_devuelta=1,
        )

        self.actualizar_detalle = simular(
            "almacen.services.DetalleEntrega.objects.filter"
        )
        self.actualizar_detalle.return_value.update.return_value = 1

        self.actualizar_producto = simular(
            "almacen.services.Producto.objects.filter"
        )
        self.actualizar_producto.return_value.update.return_value = 1

        self.movimientos = simular(
            "almacen.services.MovimientoAlmacen.objects.create"
        )

        self.usuario = SimpleNamespace(
            pk=7,
            is_authenticated=True,
            is_superuser=True,
        )

    def devolver(self, cantidad=2, detalles=None, usuario=None):
        return registrar_devolucion_materiales(
            entrega_id=4,
            detalles=detalles if detalles is not None else [
                {"detalle_id": 10, "cantidad": cantidad}
            ],
            usuario=usuario if usuario is not None else self.usuario,
        )

    def test_devolucion_correcta(self):
        resultado = self.devolver()

        self.assertEqual(resultado.pk, 4)
        self.actualizar_detalle.return_value.update.assert_called_once()
        self.actualizar_producto.return_value.update.assert_called_once()
        self.movimientos.assert_called_once()

        datos = self.movimientos.call_args.kwargs
        self.assertEqual(datos["tipo_movimiento"], "DEVOLUCION")
        self.assertEqual(datos["cantidad"], 2)
        self.assertEqual(datos["producto_id"], 3)

    def test_rechaza_cantidad_excesiva(self):
        with self.assertRaises(ValidationError):
            self.devolver(cantidad=6)

        self.movimientos.assert_not_called()

    def test_rechaza_detalles_duplicados(self):
        with self.assertRaises(ValidationError):
            self.devolver(detalles=[
                {"detalle_id": 10, "cantidad": 1},
                {"detalle_id": 10, "cantidad": 1},
            ])

        self.movimientos.assert_not_called()

    def test_rechaza_entrega_finalizada(self):
        self.entregas.return_value.get.return_value.estado = (
            "FINALIZADA"
        )

        with self.assertRaises(ValidationError):
            self.devolver()

        self.movimientos.assert_not_called()

    def test_rechaza_detalle_de_otra_entrega(self):
        self.detalles.return_value.get.side_effect = (
            DetalleEntrega.DoesNotExist
        )

        with self.assertRaises(ValidationError):
            self.devolver()

        self.movimientos.assert_not_called()

    def test_rechaza_fallo_de_actualizacion_stock(self):
        self.actualizar_producto.return_value.update.return_value = 0

        with self.assertRaises(ValidationError):
            self.devolver()

        self.movimientos.assert_not_called()

    def test_rechaza_usuario_sin_permisos(self):
        usuario = SimpleNamespace(
            is_authenticated=False,
            is_superuser=False,
        )

        with self.assertRaises(PermissionDenied):
            self.devolver(usuario=usuario)

        self.movimientos.assert_not_called()

class DevolucionVistaTests(SimpleTestCase):
    """Pruebas HTTP de la integración de HU-11."""

    def ejecutar(self, valido=True, error=None):
        request = RequestFactory().post(
            "/almacen/",
            {"accion": "registrar_devolucion"},
        )

        usuario = MagicMock()
        usuario.is_authenticated = True
        usuario.is_superuser = True
        usuario.pk = 7
        request.user = usuario

        formulario = MagicMock()
        formulario.is_valid.return_value = valido
        formulario.cleaned_data = {
            "detalle": SimpleNamespace(pk=10, entrega_id=4),
            "cantidad": 2,
            "observaciones": "Material no utilizado",
        }

        with (
            patch(
                "almacen.views.DevolucionMaterialForm",
                return_value=formulario,
            ) as clase_formulario,
            patch(
                "almacen.views.registrar_devolucion_materiales"
            ) as servicio,
            patch("almacen.views.messages.success") as mensaje,
            patch(
                "almacen.views.logger.exception"
            ) as registrar_error,
            patch(
                "almacen.views.render",
                return_value=HttpResponse("Almacén"),
            ),
        ):
            servicio.return_value = SimpleNamespace(pk=4)
            servicio.side_effect = error

            respuesta = inicio_almacen(request)

            return (
                respuesta,
                formulario,
                clase_formulario,
                servicio,
                mensaje,
                registrar_error,
            )

    def test_devolucion_valida_invoca_servicio(self):
        respuesta, formulario, clase, servicio, mensaje, _ = (
            self.ejecutar()
        )

        self.assertEqual(respuesta.status_code, 302)
        self.assertEqual(clase.call_count, 2)
        self.assertEqual(
            clase.call_args.args[0].get("accion"),
            "registrar_devolucion",
        )
        servicio.assert_called_once()

        datos = servicio.call_args.kwargs
        self.assertEqual(datos["entrega_id"], 4)
        self.assertEqual(
            datos["detalles"],
            [{"detalle_id": 10, "cantidad": 2}],
        )
        self.assertEqual(datos["usuario"].pk, 7)
        mensaje.assert_called_once()

    def test_formulario_invalido_no_registra(self):
        respuesta, _, _, servicio, mensaje, _ = (
            self.ejecutar(valido=False)
        )

        self.assertEqual(respuesta.status_code, 200)
        servicio.assert_not_called()
        mensaje.assert_not_called()

    def test_error_de_validacion_se_muestra(self):
        respuesta, formulario, _, servicio, mensaje, _ = (
            self.ejecutar(
                error=ValidationError(
                    "Cantidad superior a la disponible."
                )
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        servicio.assert_called_once()
        formulario.add_error.assert_called_once()
        mensaje.assert_not_called()

    def test_error_de_oracle_se_controla(self):
        respuesta, formulario, _, servicio, mensaje, registro = (
            self.ejecutar(
                error=DatabaseError("Error simulado de Oracle")
            )
        )

        self.assertEqual(respuesta.status_code, 200)
        servicio.assert_called_once()
        formulario.add_error.assert_called_once()
        registro.assert_called_once()
        mensaje.assert_not_called()


# HU-12: pruebas de reportes de movimientos
from datetime import date
from django.utils import timezone
from django.core.paginator import Paginator
from .forms import ReporteMovimientosForm
from .reportes import obtener_movimientos_reporte
from .reportes_views import reporte_movimientos


class ReporteMovimientosHu12Tests(SimpleTestCase):

    def test_rechaza_rango_de_fechas_invalido(self):
        formulario = ReporteMovimientosForm(data={
            "fecha_desde": "2026-11-10",
            "fecha_hasta": "2026-11-05",
        })

        self.assertFalse(formulario.is_valid())
        self.assertIn("fecha_hasta", formulario.errors)

    def test_consulta_aplica_todos_los_filtros(self):
        consulta = MagicMock()
        consulta.order_by.return_value = consulta
        consulta.filter.return_value = consulta

        with patch(
            "almacen.reportes."
            "MovimientoAlmacen.objects.select_related",
            return_value=consulta,
        ) as seleccionar:
            resultado = obtener_movimientos_reporte({
                "fecha_desde": date(2026, 11, 1),
                "fecha_hasta": date(2026, 11, 10),
                "tipo_movimiento": "DEVOLUCION",
                "producto": SimpleNamespace(pk=7),
            })

        self.assertIs(resultado, consulta)
        seleccionar.assert_called_once_with("producto")
        self.assertEqual(consulta.filter.call_count, 4)

        filtros = [
            llamada.kwargs
            for llamada in consulta.filter.call_args_list
        ]

        self.assertIn("fecha_movimiento__gte", filtros[0])
        self.assertIn("fecha_movimiento__lte", filtros[1])
        self.assertEqual(
            filtros[2], {"tipo_movimiento": "DEVOLUCION"}
        )
        self.assertEqual(filtros[3], {"producto_id": 7})

    def test_usuario_autenticado_sin_rol_almacen_puede_consultar(self):
        peticion = RequestFactory().get("/almacen/reportes/")
        peticion.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
        )

        formulario = MagicMock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {}

        with (
            patch(
                "almacen.reportes_views.ReporteMovimientosForm",
                return_value=formulario,
            ),
            patch(
                "almacen.reportes_views.obtener_movimientos_reporte",
                return_value=[],
            ) as consulta,
            patch(
                "almacen.reportes_views.render",
                return_value=HttpResponse("Reporte"),
            ) as renderizar,
        ):
            respuesta = reporte_movimientos(peticion)

        self.assertEqual(respuesta.status_code, 200)
        consulta.assert_called_once_with({})
        renderizar.assert_called_once()

    def test_paginacion_muestra_25_registros(self):
        peticion = RequestFactory().get(
            "/almacen/reportes/", {"pagina": "2"}
        )
        peticion.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
        )

        formulario = MagicMock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {}

        movimientos = [
            SimpleNamespace(pk=numero)
            for numero in range(1, 31)
        ]

        with (
            patch(
                "almacen.reportes_views.ReporteMovimientosForm",
                return_value=formulario,
            ),
            patch(
                "almacen.reportes_views.obtener_movimientos_reporte",
                return_value=movimientos,
            ),
            patch(
                "almacen.reportes_views.render",
                return_value=HttpResponse("Reporte"),
            ) as renderizar,
        ):
            respuesta = reporte_movimientos(peticion)

        pagina = renderizar.call_args.args[2]["pagina"]

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(pagina.number, 2)
        self.assertEqual(pagina.paginator.per_page, 25)
        self.assertEqual(len(pagina.object_list), 5)
        self.assertEqual(pagina.object_list[0].pk, 26)

    def test_plantilla_conserva_filtros_al_paginar(self):
        movimientos = [
            SimpleNamespace(
                pk=numero,
                fecha_movimiento=timezone.now(),
                producto=SimpleNamespace(nombre="Cable"),
                tipo_movimiento="ENTRADA",
                cantidad=1,
                id_usuario=1,
                motivo="Prueba",
                observaciones=None,
            )
            for numero in range(30)
        ]

        pagina = Paginator(movimientos, 25).get_page(2)
        peticion = RequestFactory().get(
            "/almacen/reportes/",
            {"tipo_movimiento": "ENTRADA", "pagina": "2"},
        )
        peticion.user = SimpleNamespace(is_authenticated=False)

        html = render_to_string(
            "almacen/reporte_movimientos.html",
            {"filtro_form": "", "pagina": pagina},
            request=peticion,
        )

        self.assertIn("Página 2", html)
        self.assertIn("Página anterior", html)
        self.assertIn("tipo_movimiento=ENTRADA", html)


# HU-12: validación de exportación CSV
import csv
import io

from .exportaciones import (
    LIMITE_EXPORTACION,
    exportar_movimientos_csv,
    proteger_celda,
)


class ExportacionMovimientosHu12Tests(SimpleTestCase):

    def test_protege_formulas_de_excel(self):
        for valor in ("=1+1", "+COMANDO", "-FORMULA", "@FUNCION"):
            with self.subTest(valor=valor):
                self.assertTrue(proteger_celda(valor).startswith("'"))

        self.assertTrue(
            proteger_celda("  =1+1").startswith("'")
        )
        self.assertEqual(proteger_celda("Cable óptico"), "Cable óptico")
        self.assertEqual(proteger_celda(None), "")

    def test_csv_utf8_y_contenido(self):
        movimiento = SimpleNamespace(
            pk=15,
            fecha_movimiento=timezone.now(),
            producto=SimpleNamespace(
                codigo="=1+1",
                nombre="Cable óptico",
            ),
            tipo_movimiento="DEVOLUCION",
            cantidad=3,
            id_usuario=7,
            motivo="Material recuperado",
            observaciones="Sin daños",
        )

        consulta = MagicMock()
        consulta.__getitem__.return_value.iterator.return_value = (
            iter([movimiento])
        )

        respuesta = exportar_movimientos_csv(consulta)

        self.assertTrue(respuesta.content.startswith(b"\xef\xbb\xbf"))

        contenido = respuesta.content.decode("utf-8-sig")
        filas = list(csv.reader(
            io.StringIO(contenido),
            delimiter=";",
        ))

        self.assertEqual(len(filas), 2)
        self.assertEqual(filas[1][0], "15")
        self.assertEqual(filas[1][2], "'=1+1")
        self.assertEqual(filas[1][3], "Cable óptico")
        self.assertEqual(filas[1][4], "DEVOLUCION")
        self.assertEqual(filas[1][5], "3")

    def test_exportacion_aplica_limite(self):
        consulta = MagicMock()
        consulta.__getitem__.return_value.iterator.return_value = iter([])

        exportar_movimientos_csv(consulta)

        consulta.__getitem__.assert_called_once_with(
            slice(None, LIMITE_EXPORTACION)
        )

    def test_descarga_http_autorizada(self):
        peticion = RequestFactory().get(
            "/almacen/reportes/",
            {"formato": "csv", "tipo_movimiento": "ENTRADA"},
        )
        peticion.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
        )

        formulario = MagicMock()
        formulario.is_valid.return_value = True
        formulario.cleaned_data = {
            "tipo_movimiento": "ENTRADA"
        }

        respuesta_csv = HttpResponse(
            "CSV de prueba",
            content_type="text/csv",
        )

        with (
            patch(
                "almacen.reportes_views.ReporteMovimientosForm",
                return_value=formulario,
            ),
            patch(
                "almacen.reportes_views.obtener_movimientos_reporte",
            ) as consultar,
            patch(
                "almacen.reportes_views.exportar_movimientos_csv",
                return_value=respuesta_csv,
            ) as exportar,
        ):
            respuesta = reporte_movimientos(peticion)

        self.assertIs(respuesta, respuesta_csv)
        consultar.assert_called_once_with(
            formulario.cleaned_data
        )
        exportar.assert_called_once_with(consultar.return_value)

    def test_filtros_invalidos_no_generan_csv(self):
        peticion = RequestFactory().get(
            "/almacen/reportes/",
            {"formato": "csv"},
        )
        peticion.user = SimpleNamespace(
            is_authenticated=True,
            is_superuser=True,
        )

        formulario = MagicMock()
        formulario.is_valid.return_value = False

        with (
            patch(
                "almacen.reportes_views.ReporteMovimientosForm",
                return_value=formulario,
            ),
            patch(
                "almacen.reportes_views.exportar_movimientos_csv",
            ) as exportar,
            patch(
                "almacen.reportes_views.obtener_movimientos_reporte",
            ) as consultar,
            patch(
                "almacen.reportes_views.render",
                return_value=HttpResponse("Filtros inválidos"),
            ),
        ):
            respuesta = reporte_movimientos(peticion)

        self.assertEqual(respuesta.status_code, 200)
        exportar.assert_not_called()
        consultar.assert_not_called()
