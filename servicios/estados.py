"""
Patrón State para los estados del contrato (RN-03).

Un contrato solo puede estar en: activo, suspendido o cancelado.
Transiciones permitidas:
    activo     -> suspendido, cancelado
    suspendido -> activo, cancelado
    cancelado  -> (ninguna: es un estado final)
"""
from .exceptions import TransicionInvalidaError

ACTIVO = "ACTIVO"
SUSPENDIDO = "SUSPENDIDO"
CANCELADO = "CANCELADO"

OPCIONES_ESTADO = [
    (ACTIVO, "Activo"),
    (SUSPENDIDO, "Suspendido"),
    (CANCELADO, "Cancelado"),
]


class EstadoContrato:
    codigo = None
    transiciones = ()

    def puede_cambiar_a(self, nuevo):
        return nuevo in self.transiciones

    def validar_cambio(self, nuevo):
        if not self.puede_cambiar_a(nuevo):
            raise TransicionInvalidaError(
                f"No se puede pasar de {self.codigo.lower()} a {nuevo.lower()} (RN-03)."
            )

    def permite_incidencias(self):
        # RN-04: solo contratos activos pueden registrar incidencias.
        return False


class EstadoActivo(EstadoContrato):
    codigo = ACTIVO
    transiciones = (SUSPENDIDO, CANCELADO)

    def permite_incidencias(self):
        return True


class EstadoSuspendido(EstadoContrato):
    codigo = SUSPENDIDO
    transiciones = (ACTIVO, CANCELADO)


class EstadoCancelado(EstadoContrato):
    codigo = CANCELADO
    transiciones = ()


_ESTADOS = {
    ACTIVO: EstadoActivo(),
    SUSPENDIDO: EstadoSuspendido(),
    CANCELADO: EstadoCancelado(),
}


def obtener_estado(codigo):
    return _ESTADOS[codigo]
