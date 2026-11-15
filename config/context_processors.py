
def menu_wintv(request):
    usuario = request.user

    menu = [
        {
            "nombre": "🏠 Inicio",
            "url": "/",
        }
    ]

    roles = set()

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
                    "nombre": "👥 Registrar clientes",
                    "url": "/clientes/registrar/",
                },
                {
                    "nombre": "🔎 Buscar clientes",
                    "url": "/clientes/buscar/",
                },
            ])

        # ==========================================
        # MODULO ADMINISTRATIVO
        # ==========================================
        if "ADMINISTRADOR" in roles:
            menu.append({
                "nombre": "🔐 Usuarios",
                "url": "/usuarios/listar/",
            })

        # ==========================================
        # MODULO DE ALMACEN Y HU-09
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "ALMACEN",
        }):
            menu.extend([
                {
                    "nombre": "📦 Almacén",
                    "url": "/almacen/",
                },
                {
                    "nombre": "🖥️ Asignar equipos a clientes",
                    "url": "/almacen/equipos-clientes/asignar/",
                },
            ])
        # HU-17: Registrar materiales utilizados en reparación
        if roles.intersection({
            "ADMINISTRADOR",
            "TECNICO",
        }):
            menu.append({
                "nombre": "🔧 Registrar materiales utilizados",
                "url": "/almacen/materiales-usados/",
            })
        # ==========================================
        # HU-02: GESTION DE CONTRATOS
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "VENDEDOR",
            "CAJA",
        }):
            menu.append({
                "nombre": "📄 Consultar contratos",
                "url": "/servicios/contratos/",
            })

        # ==========================================
        # MODULO DE SOPORTE TECNICO
        # HU-13, HU-16, HU-18 Y HU-19
        # ==========================================
        if roles.intersection({
            "ADMINISTRADOR",
            "TECNICO",
        }):
            menu.extend([
                {
                    # HU-13
                    "nombre": "🛠 Registrar incidencias",
                    "url": "/incidencias/registrar/",
                },
                {
                    # HU-13 y HU-14
                    "nombre": "📋 Consultar incidencias",
                    "url": "/incidencias/listar/",
                },
                {
                    # HU-16
                    "nombre": "🩺 Diagnósticos técnicos",
                    "url": "/incidencias/diagnosticos/",
                },
                {
                    # HU-18
                    "nombre": "🔄 Estados de órdenes",
                    "url": "/incidencias/ordenes/estados/",
                },
                {
                    # HU-19
                    # Texto sin emoji para evitar problemas
                    # de codificacion.
                    "nombre": "Historial de incidencias",
                    "url": "/incidencias/historial/",
                },
            ])

    else:
        menu.append({
            "nombre": "🔑 Iniciar sesión",
            "url": "/usuarios/login/",
        })

    return {
        "menu_wintv": menu,
        "roles_wintv": (
            ", ".join(sorted(roles))
            if roles else "Sin rol"
        ),
    }
