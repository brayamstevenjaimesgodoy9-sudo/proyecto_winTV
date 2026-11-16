
from django.db import migrations


# HU-13: Cargar el catalogo inicial de tipos de averia.
# No duplicar registros existentes.


def cargar_tipos_averia(apps, schema_editor):

    tipos = [
        (
            "Cortes intermitentes",
            "Perdidas frecuentes de conexion",
        ),
        (
            "Falla de senal WiFi",
            "Problemas de cobertura inalambrica",
        ),
        (
            "Internet lento",
            "Velocidad inferior a la contratada",
        ),
        (
            "Problemas de cableado",
            "Cableado de red o fibra danado",
        ),
        (
            "Problemas de router",
            "Fallas en el router o configuracion",
        ),
        (
            "Sin conexion a internet",
            "Cliente sin acceso a internet",
        ),
    ]

    with schema_editor.connection.cursor() as cursor:

        for nombre, descripcion in tipos:

            cursor.execute(
                """
                SELECT 1
                FROM TIPO_AVERIA
                WHERE NOMBRE = %s
                """,
                [nombre],
            )

            if cursor.fetchone() is None:

                cursor.execute(
                    """
                    INSERT INTO TIPO_AVERIA
                        (NOMBRE, DESCRIPCION, ACTIVO)
                    VALUES (%s, %s, %s)
                    """,
                    [nombre, descripcion, 1],
                )


class Migration(migrations.Migration):

    dependencies = []

    operations = [
        migrations.RunPython(
            cargar_tipos_averia,
            migrations.RunPython.noop,
        ),
    ]
