from django.db import transaction
from django.core.exceptions import ValidationError
from . import estados
from .models import Contrato, Plan
from clientes.models import Cliente

class ContratoService:
    @transaction.atomic
    def registrar_contrato(self, cliente, plan, fecha_inicio, direccion_instalacion):
        if not Plan.objects.filter(pk=plan.pk, activo=1).exists():
            raise ValidationError("El plan no está activo")
        if not Cliente.objects.filter(pk=cliente.pk, activo=1).exists():
            raise ValidationError("El cliente no está activo")
        return Contrato.objects.create(cliente=cliente, plan=plan, fecha_inicio=fecha_inicio,
            direccion_instalacion=direccion_instalacion, estado=estados.ACTIVO)
    @transaction.atomic
    def actualizar(self, contrato, plan, direccion_instalacion):
        if contrato.estado == estados.CANCELADO:
            raise ValidationError("No se puede editar un contrato cancelado")
        if not Plan.objects.filter(pk=plan.pk, activo=1).exists():
            raise ValidationError("El plan no está activo")
        contrato.plan=plan
        contrato.direccion_instalacion=direccion_instalacion
        contrato.save(update_fields=["plan", "direccion_instalacion"])
        return contrato
    @transaction.atomic
    def cambiar_estado(self, contrato, nuevo_estado):
        contrato.estado_obj.validar_cambio(nuevo_estado)
        contrato.estado=nuevo_estado
        contrato.save(update_fields=["estado"])
        return contrato
