from django.db import models


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