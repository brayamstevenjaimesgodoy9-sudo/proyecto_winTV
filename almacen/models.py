from django.conf import settings
from django.db import models
from django.utils import timezone


class Producto(models.Model):
    id_producto = models.BigAutoField(
        primary_key=True,
        db_column="ID_PRODUCTO"
    )
    codigo = models.CharField(
        max_length=30,
        unique=True,
        db_column="CODIGO"
    )
    nombre = models.CharField(
        max_length=100,
        db_column="NOMBRE"
    )
    descripcion = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        db_column="DESCRIPCION"
    )
    categoria = models.CharField(
        max_length=50,
        db_column="CATEGORIA"
    )
    unidad_medida = models.CharField(
        max_length=20,
        db_column="UNIDAD_MEDIDA"
    )
    stock_actual = models.IntegerField(
        default=0,
        db_column="STOCK_ACTUAL"
    )
    stock_minimo = models.IntegerField(
        default=0,
        db_column="STOCK_MINIMO"
    )
    activo = models.IntegerField(
        default=1,
        db_column="ACTIVO"
    )

    class Meta:
        managed = False
        db_table = "PRODUCTO"

    def __str__(self):
        return self.nombre


class MovimientoAlmacen(models.Model):
    id_movimiento = models.BigAutoField(
        primary_key=True,
        db_column="ID_MOVIMIENTO"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.DO_NOTHING,
        db_column="ID_PRODUCTO"
    )
    id_usuario = models.IntegerField(
        db_column="ID_USUARIO"
    )
    tipo_movimiento = models.CharField(
        max_length=20,
        db_column="TIPO_MOVIMIENTO"
    )
    cantidad = models.IntegerField(
        db_column="CANTIDAD"
    )
    fecha_movimiento = models.DateTimeField(
        db_column="FECHA_MOVIMIENTO"
    )
    motivo = models.CharField(
        max_length=250,
        db_column="MOTIVO"
    )
    observaciones = models.CharField(
        max_length=500,
        null=True,
        blank=True,
        db_column="OBSERVACIONES"
    )

    class Meta:
        managed = False
        db_table = "MOVIMIENTO_ALMACEN"

class OrdenTrabajo(models.Model):
    id_orden = models.BigAutoField(
        primary_key=True, db_column="ID_ORDEN"
    )
    id_contrato = models.BigIntegerField(db_column="ID_CONTRATO")
    id_incidencia = models.BigIntegerField(
        db_column="ID_INCIDENCIA", null=True, blank=True
    )
    tipo_orden = models.CharField(max_length=20, db_column="TIPO_ORDEN")
    fecha_creacion = models.DateTimeField(db_column="FECHA_CREACION")
    fecha_programada = models.DateTimeField(
        db_column="FECHA_PROGRAMADA", null=True, blank=True
    )
    estado = models.CharField(max_length=20, db_column="ESTADO")
    diagnostico = models.CharField(
        max_length=1000, db_column="DIAGNOSTICO",
        null=True, blank=True
    )
    solucion = models.CharField(
        max_length=1000, db_column="SOLUCION",
        null=True, blank=True
    )
    observaciones = models.CharField(
        max_length=500, db_column="OBSERVACIONES",
        null=True, blank=True
    )

    class Meta:
        managed = False
        db_table = "ORDEN_TRABAJO"

    def __str__(self):
        return f"Orden #{self.pk} - {self.tipo_orden}"


class AsignacionTecnico(models.Model):
    id_asignacion = models.BigAutoField(
        primary_key=True, db_column="ID_ASIGNACION"
    )
    orden = models.ForeignKey(
        OrdenTrabajo,
        on_delete=models.PROTECT,
        db_column="ID_ORDEN",
        related_name="asignaciones_tecnicos",
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="ID_USUARIO",
        related_name="asignaciones_wintv",
    )
    fecha_asignacion = models.DateTimeField(
        db_column="FECHA_ASIGNACION"
    )
    estado = models.CharField(max_length=20, db_column="ESTADO")
    observaciones = models.CharField(
        max_length=500, db_column="OBSERVACIONES",
        null=True, blank=True
    )

    class Meta:
        managed = False
        db_table = "ASIGNACION_TECNICO"


class EntregaMaterial(models.Model):
    id_entrega = models.BigAutoField(
        primary_key=True, db_column="ID_ENTREGA"
    )
    orden = models.ForeignKey(
        OrdenTrabajo,
        on_delete=models.PROTECT,
        db_column="ID_ORDEN",
        related_name="entregas_material",
    )
    tecnico = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        db_column="ID_USUARIO_TECNICO",
        related_name="entregas_material_wintv",
    )
    fecha_entrega = models.DateTimeField(
        default=timezone.now, db_column="FECHA_ENTREGA"
    )
    estado = models.CharField(
        max_length=20, default="ENTREGADA", db_column="ESTADO"
    )
    observaciones = models.CharField(
        max_length=500, db_column="OBSERVACIONES",
        null=True, blank=True
    )

    class Meta:
        managed = False
        db_table = "ENTREGA_MATERIAL"


class DetalleEntrega(models.Model):
    id_detalle = models.BigAutoField(
        primary_key=True, db_column="ID_DETALLE"
    )
    entrega = models.ForeignKey(
        EntregaMaterial,
        on_delete=models.PROTECT,
        db_column="ID_ENTREGA",
        related_name="detalles",
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column="ID_PRODUCTO",
        related_name="detalles_entrega",
    )
    cantidad_entregada = models.IntegerField(
        db_column="CANTIDAD_ENTREGADA"
    )
    cantidad_utilizada = models.IntegerField(
        default=0, db_column="CANTIDAD_UTILIZADA"
    )
    cantidad_devuelta = models.IntegerField(
        default=0, db_column="CANTIDAD_DEVUELTA"
    )

    class Meta:
        managed = False
        db_table = "DETALLE_ENTREGA"
