
from types import SimpleNamespace
from unittest.mock import Mock

from django.test import SimpleTestCase
from config.context_processors import menu_wintv


class PruebasSprint2Tecnico(SimpleTestCase):

    def test_acceso_tecnico_incidente(self):
        grupos = Mock()
        grupos.values_list.return_value = ["TECNICO"]

        usuario = SimpleNamespace(
            is_authenticated=True,
            is_superuser=False,
            groups=grupos
        )

        request = SimpleNamespace(user=usuario)
        resultado = menu_wintv(request)

        menu = resultado["menu_wintv"]

        # Obtener rutas, incluidas las de submenus
        opciones = []
        for opcion in menu:
            if opcion.get("tipo") == "grupo":
                opciones.extend(opcion["items"])
            else:
                opciones.append(opcion)

        rutas = [op["url"] for op in opciones]

        # El tecnico puede registrar y consultar
        self.assertIn(
            "/incidencias/registrar/", rutas
        )
        self.assertIn(
            "/incidencias/listar/", rutas
        )

        # No debe tener la opcion de administrar usuarios
        self.assertNotIn(
            "/usuarios/listar/", rutas
        )
