"""
Exportación segura de movimientos de almacén (HU-12).
"""

import csv

from django.http import HttpResponse
from django.utils import timezone


LIMITE_EXPORTACION = 10000


def proteger_celda(valor):
    """Evita interpretar texto del usuario como fórmula en Excel."""
    if valor is None:
        return ""

    texto = str(valor)
    texto = texto.replace("\r", " ")
    texto = texto.replace("\n", " ")
    texto = texto.replace("\t", " ")

    if texto.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + texto

    return texto


def exportar_movimientos_csv(movimientos):
    """Exporta hasta 10 000 movimientos filtrados."""
    respuesta = HttpResponse(
        content_type="text/csv; charset=utf-8"
    )

    respuesta["Content-Disposition"] = (
        'attachment; filename="wintv_movimientos.csv"'
    )

    # BOM: facilita la lectura de caracteres UTF-8 en Excel.
    respuesta.write("\ufeff")

    escritor = csv.writer(
        respuesta,
        delimiter=";",
        lineterminator="\r\n",
    )

    escritor.writerow([
        "ID",
        "Fecha",
        "Código de producto",
        "Producto",
        "Tipo de movimiento",
        "Cantidad",
        "Usuario ID",
        "Motivo",
        "Observaciones",
    ])

    for movimiento in movimientos[:LIMITE_EXPORTACION].iterator(
        chunk_size=500
    ):
        escritor.writerow([
            movimiento.pk,
            timezone.localtime(
                movimiento.fecha_movimiento
            ).strftime("%d/%m/%Y %H:%M"),
            proteger_celda(movimiento.producto.codigo),
            proteger_celda(movimiento.producto.nombre),
            proteger_celda(movimiento.tipo_movimiento),
            movimiento.cantidad,
            movimiento.id_usuario,
            proteger_celda(movimiento.motivo),
            proteger_celda(movimiento.observaciones),
        ])

    return respuesta
