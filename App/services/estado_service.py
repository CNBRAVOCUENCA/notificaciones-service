"""Servicio de estado: registra transiciones de estado de los documentos.

Cada vez que otro microservicio informa un avance (subido, extraido,
resumido...), este servicio valida el estado, lo registra como estado
actual, y lo agrega al historial del documento.
"""

from App.exceptions import DocumentoNoEncontradoError, EstadoInvalidoError
from App.models.estado_documento import ESTADOS_VALIDOS, EstadoDocumento, EventoEstado
from App.repositories.estado_repository import EstadoRepository


class EstadoService:
    def __init__(self, repository: EstadoRepository):
        self.repository = repository

    def actualizar_estado(self, document_id: int, estado: str, detalle: str = "") -> EstadoDocumento:
        if estado not in ESTADOS_VALIDOS:
            raise EstadoInvalidoError(
                f"Estado '{estado}' inválido. Válidos: {', '.join(ESTADOS_VALIDOS)}"
            )

        evento = EventoEstado(estado=estado, detalle=detalle)
        return self.repository.registrar_evento(document_id, evento)

    def obtener_estado(self, document_id: int) -> EstadoDocumento:
        estado = self.repository.get_by_document_id(document_id)
        if estado is None:
            raise DocumentoNoEncontradoError(f"No hay registro de estado para el documento {document_id}")
        return estado

    def listar(self, skip: int = 0, limit: int = 50) -> list[EstadoDocumento]:
        return self.repository.get_all(skip, limit)
