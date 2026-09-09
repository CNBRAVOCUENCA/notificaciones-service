"""Excepciones de dominio del microservicio de Notificaciones / Estado."""


class NotificacionesException(Exception):
    """Excepción base para errores de negocio de este servicio."""


class EstadoInvalidoError(NotificacionesException):
    """El estado indicado no es uno de los estados válidos del flujo."""


class DocumentoNoEncontradoError(NotificacionesException):
    """No hay registro de estado para el documento solicitado."""
