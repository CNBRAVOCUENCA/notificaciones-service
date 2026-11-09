"""Repositorio de estados de documentos: acceso a datos en MongoDB."""

from typing import Any

from pymongo import ReturnDocument

from App.models.estado_documento import EstadoDocumento, EventoEstado


class EstadoRepository:
    def __init__(self, db: Any):
        self.collection = db["estados"]

    def get_by_document_id(self, document_id: int) -> EstadoDocumento | None:
        payload = self.collection.find_one({"document_id": document_id})
        return self._deserialize(payload)

    def registrar_evento(self, document_id: int, evento: EventoEstado) -> EstadoDocumento:
        """Agrega un evento al historial y lo marca como estado actual.

        Es una sola operación atómica en MongoDB ($push + $set con upsert): no
        lee antes de escribir, así que dos notificaciones simultáneas del mismo
        documento no se pisan y no se pierde ningún evento del historial.
        """
        evento_json = evento.model_dump(mode="json")
        payload = self.collection.find_one_and_update(
            {"document_id": document_id},
            {
                "$set": {"estado_actual": evento.estado, "updated_at": evento_json["timestamp"]},
                "$push": {"historial": evento_json},
                "$setOnInsert": {"document_id": document_id},
            },
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        return self._deserialize(payload)

    def get_all(self, skip: int = 0, limit: int = 50) -> list[EstadoDocumento]:
        cursor = self.collection.find().skip(skip).limit(limit)
        return [self._deserialize(p) for p in cursor]

    def _deserialize(self, payload: dict | None) -> EstadoDocumento | None:
        if payload is None:
            return None
        payload = {k: v for k, v in payload.items() if k != "_id"}
        return EstadoDocumento(**payload)
