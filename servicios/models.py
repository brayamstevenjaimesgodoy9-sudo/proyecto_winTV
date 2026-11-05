from django.db import models
from django.utils import timezone
from . import estados

class Plan(models.Model):
    id_plan = models.BigAutoField(primary_key=True, db_column="ID_PLAN")
    nombre = models.CharField(max_length=100, db_column="NOMBRE")
    velocidad_mbps = models.DecimalField(max_digits=10, decimal_places=0, db_column="VELOCIDAD_MBPS")
    precio_mensual = models.DecimalField(max_digits=10, decimal_places=2, db_column="PRECIO_MENSUAL")
    descripcion = models.CharField(max_length=250, null=True, blank=True, db_column="DESCRIPCION")
    activo = models.IntegerField(default=1, db_column="ACTIVO")
    class Meta:
        managed = False
        db_table = "PLAN_SERVICIO"
    def __str__(self):
        return f"{self.nombre} ({self.velocidad_mbps} Mbps)"

class Contrato(models.Model):
    id_contrato = models.BigAutoField(primary_key=True, db_column="ID_CONTRATO")
    cliente = models.ForeignKey("clientes.Cliente", db_column="ID_CLIENTE", on_delete=models.PROTECT, related_name="contratos")
    plan = models.ForeignKey(Plan, db_column="ID_PLAN", on_delete=models.PROTECT, related_name="contratos")
    fecha_inicio = models.DateField(default=timezone.localdate, db_column="FECHA_INICIO")
    direccion_instalacion = models.CharField(max_length=200, db_column="DIRECCION_INSTALACION")
    estado = models.CharField(max_length=20, choices=estados.OPCIONES_ESTADO, default=estados.ACTIVO, db_column="ESTADO")
    class Meta:
        managed = False
        db_table = "CONTRATO"
    @property
    def codigo(self):
        return f"CTR-{self.pk:06d}" if self.pk is not None else "Sin asignar"
    @property
    def estado_obj(self):
        return estados.obtener_estado(self.estado)
    def estados_disponibles(self):
        return [(c,n) for c,n in estados.OPCIONES_ESTADO if self.estado_obj.puede_cambiar_a(c)]
    def __str__(self):
        return f"{self.codigo} - {self.cliente}"
