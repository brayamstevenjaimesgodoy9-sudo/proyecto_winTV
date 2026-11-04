from django.db import models


class Cliente(models.Model):
    id_cliente = models.BigAutoField(
        primary_key=True,
        db_column="ID_CLIENTE"
    )

    tipo_documento = models.CharField(
        max_length=20,
        db_column="TIPO_DOCUMENTO"
    )

    numero_documento = models.CharField(
        max_length=20,
        db_column="NUMERO_DOCUMENTO"
    )

    nombres = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column="NOMBRES"
    )

    apellidos = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_column="APELLIDOS"
    )

    razon_social = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        db_column="RAZON_SOCIAL"
    )

    direccion = models.CharField(
        max_length=200,
        db_column="DIRECCION"
    )

    zona = models.CharField(
        max_length=100,
        db_column="ZONA"
    )

    telefono = models.CharField(
        max_length=20,
        null=True,
        blank=True,
        db_column="TELEFONO"
    )

    correo = models.CharField(
        max_length=150,
        null=True,
        blank=True,
        db_column="CORREO"
    )

    activo = models.IntegerField(
        default=1,
        db_column="ACTIVO"
    )

    class Meta:
        managed = False
        db_table = "CLIENTE"

    def __str__(self):
        return (
            self.razon_social
            or f"{self.nombres or ''} {self.apellidos or ''}".strip()
        )

