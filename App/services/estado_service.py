"""Servicio de estado: registra transiciones de estado de los documentos.

Cada vez que otro microservicio informa un avance (subido, extraido,
resumido...), este servicio valida el estado, lo registra como estado
actual, y lo agrega al historial del documento.
"""

from App.exceptions import (
    ConflictoEstadoError,
    DocumentoNoEncontradoError,
    EstadoInvalidoError,
    TransicionEstadoInvalidaError,
)
from App.models.estado_documento import (
    ESTADOS_VALIDOS,
    TRANSICIONES_PERMITIDAS,
    EstadoDocumento,
    EventoEstado,
)
from App.repositories.estado_repository import EstadoRepository


class EstadoService:
    MAX_INTENTOS_TRANSICION = 3

    def __init__(self, repository: EstadoRepository):
        self.repository = repository

    def actualizar_estado(self, document_id: int, estado: str, detalle: str = "") -> EstadoDocumento:
        if estado not in ESTADOS_VALIDOS:
            raise EstadoInvalidoError(f"Estado '{estado}' inválido. Válidos: {', '.join(ESTADOS_VALIDOS)}")

        evento = EventoEstado(estado=estado, detalle=detalle)
        for _ in range(self.MAX_INTENTOS_TRANSICION):
            actual = self.repository.get_by_document_id(document_id)
            estado_actual = actual.estado_actual if actual else None

            if estado_actual == estado:
                return actual
            if estado_actual is None:
                transicion_permitida = estado == "subido"
            else:
                transicion_permitida = estado in TRANSICIONES_PERMITIDAS.get(estado_actual, set())
            if not transicion_permitida:
                origen = estado_actual or "sin estado"
                raise TransicionEstadoInvalidaError(f"No se permite la transición de '{origen}' a '{estado}'")

            actualizado = self.repository.registrar_evento_si_estado_actual(document_id, evento, estado_actual)
            if actualizado is not None:
                return actualizado

        raise ConflictoEstadoError(f"El estado del documento {document_id} cambió concurrentemente; vuelve a intentar")

    def obtener_estado(self, document_id: int) -> EstadoDocumento:
        estado = self.repository.get_by_document_id(document_id)
        if estado is None:
            raise DocumentoNoEncontradoError(f"No hay registro de estado para el documento {document_id}")
        return estado

    def listar(self, skip: int = 0, limit: int = 50) -> list[EstadoDocumento]:
        return self.repository.get_all(skip, limit)
