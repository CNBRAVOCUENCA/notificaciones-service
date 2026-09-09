"""Repositorio de estados de documentos: acceso a datos en MongoDB."""

from typing import Any, Optional

from App.models.estado_documento import EstadoDocumento


class EstadoRepository:
    def __init__(self, db: Any):
        self.collection = db["estados"]

    def get_by_document_id(self, document_id: int) -> Optional[EstadoDocumento]:
        payload = self.collection.find_one({"document_id": document_id})
        return self._deserialize(payload)

    def upsert(self, estado: EstadoDocumento) -> EstadoDocumento:
        """Inserta o actualiza el estado de un documento (por document_id)."""
        self.collection.update_one(
            {"document_id": estado.document_id},
            {"$set": self._serialize(estado)},
            upsert=True,
        )
        return estado

    def get_all(self, skip: int = 0, limit: int = 50) -> list[EstadoDocumento]:
        cursor = self.collection.find().skip(skip).limit(limit)
        return [self._deserialize(p) for p in cursor]

    def _serialize(self, estado: EstadoDocumento) -> dict:
        return estado.model_dump(mode="json")

    def _deserialize(self, payload: Optional[dict]) -> Optional[EstadoDocumento]:
        if payload is None:
            return None
        payload = {k: v for k, v in payload.items() if k != "_id"}
        return EstadoDocumento(**payload)
