
from django.db import models
from django.utils import timezone


# HU-14: Tipos de averías
class TipoAveria(models.Model):
    id_tipo_averia = models.BigAutoField(
        primary_key=True,
        db_column='ID_TIPO_AVERIA'
    )

    nombre = models.CharField(
        max_length=100,
        db_column='NOMBRE'
    )

    descripcion = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        db_column='DESCRIPCION'
    )

    activo = models.IntegerField(
        default=1,
        db_column='ACTIVO'
    )

    class Meta:
        managed = False
        db_table = 'TIPO_AVERIA'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# HU-13: Registro de incidencias
class Incidencia(models.Model):
    id_incidencia = models.BigAutoField(
        primary_key=True,
        db_column='ID_INCIDENCIA'
    )

    id_cliente = models.BigIntegerField(
        db_column='ID_CLIENTE'
    )

    id_contrato = models.BigIntegerField(
        db_column='ID_CONTRATO'
    )

    tipo_averia = models.ForeignKey(
        TipoAveria,
        on_delete=models.PROTECT,
        db_column='ID_TIPO_AVERIA'
    )

    fecha_reporte = models.DateTimeField(
        default=timezone.now,
        db_column='FECHA_REPORTE'
    )

    descripcion = models.CharField(
        max_length=500,
        db_column='DESCRIPCION'
    )

    canal_reporte = models.CharField(
        max_length=30,
        db_column='CANAL_REPORTE'
    )

    ubicacion = models.CharField(
        max_length=200,
        db_column='UBICACION'
    )

    prioridad = models.CharField(
    max_length=20,
    choices=[
        ('BAJA', 'Baja'),
        ('MEDIA', 'Media'),
        ('ALTA', 'Alta'),
        ('CRITICA', 'Crítica'),
    ],
    default='MEDIA',
    db_column='PRIORIDAD'
)

    estado = models.CharField(
        max_length=30,
        default='REGISTRADA',
        db_column='ESTADO'
)

    class Meta:
        managed = False
        db_table = 'INCIDENCIA'
        ordering = ['-fecha_reporte']

    def __str__(self):
        return f'Incidencia #{self.id_incidencia}'
