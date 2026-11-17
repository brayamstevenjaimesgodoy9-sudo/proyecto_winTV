
def menu_wintv(request):
    usuario = request.user
    roles = set()

    menu = [
        {
            "nombre": "Inicio",
            "url": "/",
        }
    ]

    if usuario.is_authenticated:

        roles = {
            nombre.strip().upper()
            for nombre in usuario.groups.values_list(
                "name", flat=True
            )
        }

        if usuario.is_superuser:
            roles.add("ADMINISTRADOR")

        # ==========================================
        # MODULO DE CLIENTES
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "VENDEDOR",
        }):
            menu.extend([
                {
                    "nombre": "Registrar clientes",
                    "url": "/clientes/registrar/",
                },
                {
                    "nombre": "Buscar clientes",
                    "url": "/clientes/buscar/",
                },
            ])

        # ==========================================
        # MODULO ADMINISTRATIVO
        # ==========================================
        if "ADMINISTRADOR" in roles:
            menu.append({
                "nombre": "Usuarios",
                "url": "/usuarios/listar/",
            })

        # ==========================================
        # ALMACEN
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "ALMACEN",
        }):
            menu.extend([
                {
                    "nombre": "Almacén",
                    "url": "/almacen/",
                },
                {
                    "nombre": "Asignar equipos a clientes",
                    "url": "/almacen/equipos-clientes/asignar/",
                },
            ])

        # HU-12: Reportes de almacen
        # Disponible para usuarios autenticados.
        menu.append({
            "nombre": "Reportes de almacén",
            "url": "/almacen/reportes/",
        })

        # ==========================================
        # HU-17: MATERIALES UTILIZADOS
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "TECNICO",
        }):
            menu.append({
                "nombre": "Registrar materiales utilizados",
                "url": "/almacen/materiales-usados/",
            })

        # ==========================================
        # HU-02: CONTRATOS
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "VENDEDOR",
            "CAJA",
        }):
            menu.append({
                "nombre": "Consultar contratos",
                "url": "/servicios/contratos/",
            })

        # ==========================================
        # SOPORTE TECNICO
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "TECNICO",
        }):

            # GRUPO DESPLEGABLE:
            # REGISTRAR, CONSULTAR E HISTORIAL
            menu.append({
                "tipo": "grupo",
                "nombre": "Incidencias",
                "url": "/incidencias/listar/",
                "grupo": "SOPORTE TÉCNICO",
                "icono": "clipboard-list",
                "orden": 31,
                "items": [
                    {
                        "nombre": "Registrar incidencias",
                        "url": "/incidencias/registrar/",
                        "icono": "alert-circle",
                    },
                    {
                        "nombre": "Consultar incidencias",
                        "url": "/incidencias/listar/",
                        "icono": "clipboard-list",
                    },
                    {
                        "nombre": "Historial de incidencias",
                        "url": "/incidencias/historial/",
                        "icono": "history",
                    },
                ],
            })

            # LAS DEMAS FUNCIONES SE CONSERVAN
            menu.extend([
                {
                    "nombre": "Asignar órdenes de trabajo",
                    "url": "/incidencias/asignar-orden/",
                },
                {
                    "nombre": "Diagnósticos técnicos",
                    "url": "/incidencias/diagnosticos/",
                },
                {
                    "nombre": "Estados de órdenes",
                    "url": "/incidencias/ordenes/estados/",
                },
            ])

    else:
        menu.append({
            "nombre": "Iniciar sesión",
            "url": "/usuarios/login/",
        })

    # ==========================================
    # METADATOS DE NAVEGACION
    # ==========================================
    navegacion = {
        "/": ("GENERAL", "home", 0),

        "/usuarios/login/": (
            "GENERAL", "log-in", 1
        ),

        # CLIENTES
        "/clientes/registrar/": (
            "GESTIÓN COMERCIAL", "user-plus", 10
        ),
        "/clientes/buscar/": (
            "GESTIÓN COMERCIAL", "users", 11
        ),

        # CONTRATOS
        "/servicios/contratos/": (
            "GESTIÓN COMERCIAL", "file-text", 12
        ),

        # ALMACEN
        "/almacen/": (
            "ALMACÉN", "package", 20
        ),
        "/almacen/equipos-clientes/asignar/": (
            "ALMACÉN", "monitor", 21
        ),
        "/almacen/reportes/": (
            "ALMACÉN", "activity", 22
        ),

        # SOPORTE TECNICO
        "/almacen/materiales-usados/": (
            "SOPORTE TÉCNICO", "wrench", 30
        ),

        # GRUPO INCIDENCIAS
        "/incidencias/registrar/": (
            "SOPORTE TÉCNICO", "alert-circle", 31
        ),
        "/incidencias/listar/": (
            "SOPORTE TÉCNICO", "clipboard-list", 31
        ),
        "/incidencias/historial/": (
            "SOPORTE TÉCNICO", "history", 31
        ),

        # ORDENES Y DIAGNOSTICOS
        "/incidencias/asignar-orden/": (
            "SOPORTE TÉCNICO", "clipboard-check", 33
        ),
        "/incidencias/diagnosticos/": (
            "SOPORTE TÉCNICO", "stethoscope", 34
        ),
        "/incidencias/ordenes/estados/": (
            "SOPORTE TÉCNICO", "activity", 35
        ),

        # ADMINISTRACION
        "/usuarios/listar/": (
            "ADMINISTRACIÓN", "settings", 50
        ),
    }

    # ==========================================
    # ASIGNAR GRUPOS E ICONOS
    # ==========================================
    for opcion in menu:

        if opcion.get("tipo") == "grupo":

            for subopcion in opcion["items"]:
                subopcion["grupo"] = opcion["grupo"]

            continue

        grupo, icono, orden = navegacion.get(
            opcion["url"],
            ("OTROS", "grid", 99),
        )

        opcion["grupo"] = grupo
        opcion["icono"] = icono

    # ==========================================
    # ORDENAR MENU
    # ==========================================
    menu.sort(
        key=lambda opcion: opcion.get(
            "orden",
            navegacion.get(
                opcion.get("url"),
                ("OTROS", "grid", 99),
            )[2],
        )
    )

    return {
        "menu_wintv": menu,
        "roles_wintv": (
            ", ".join(sorted(roles))
            if roles else "Sin rol"
        ),
    }
