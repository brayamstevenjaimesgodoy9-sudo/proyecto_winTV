
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

        # Acceso visual al módulo de clientes
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

        # Menú administrativo
        if "ADMINISTRADOR" in roles:
            menu.append({
                "nombre": "🔐 Usuarios",
                "url": "/usuarios/listar/",
            })

    else:
        menu.append({
            "nombre": "🔑 Iniciar sesión",
            "url": "/usuarios/login/",
        })

    return {
        "menu_wintv": menu,
        "roles_wintv": ", ".join(sorted(roles))
                       if roles else "Sin rol",
    }
