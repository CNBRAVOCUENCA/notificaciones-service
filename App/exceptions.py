"""Excepciones de dominio del microservicio de Notificaciones / Estado."""


class NotificacionesException(Exception):
    """Excepción base para errores de negocio de este servicio."""


class EstadoInvalidoError(NotificacionesException):
    """El estado indicado no es uno de los estados válidos del flujo."""


class TransicionEstadoInvalidaError(NotificacionesException):
    """La transición solicitada no está permitida desde el estado actual."""


class ConflictoEstadoError(NotificacionesException):
    """El estado cambió concurrentemente y no se pudo aplicar la transición."""


class DocumentoNoEncontradoError(NotificacionesException):
    """No hay registro de estado para el documento solicitado."""
