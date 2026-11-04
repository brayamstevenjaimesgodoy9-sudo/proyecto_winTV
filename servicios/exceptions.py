"""Excepciones propias de la app servicios (informe: "Código limpio")."""


class TransicionInvalidaError(Exception):
    """Cambio de estado del contrato no permitido (RN-03)."""


class PlanNoVigenteError(Exception):
    """Se intentó usar un plan que no está vigente (RN-02)."""


class ContratoCanceladoError(Exception):
    """Un contrato cancelado no admite cambios de plan ni de dirección."""


class ContratoInactivoError(Exception):
    """
    El contrato no está activo (RN-04).
    La usará Soporte Técnico (Alex, HU-13) antes de registrar una incidencia:
        ContratoService.verificar_activo(contrato)
    """
