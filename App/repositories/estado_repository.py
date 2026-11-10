"""Repositorio de estados de documentos: acceso a datos en MongoDB."""

from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from App.models.estado_documento import EstadoDocumento, EventoEstado


class EstadoRepository:
    def __init__(self, db: Any):
        self.collection = db["estados"]

    def get_by_document_id(self, document_id: int) -> EstadoDocumento | None:
        payload = self.collection.find_one({"document_id": document_id})
        return self._deserialize(payload)

    def registrar_evento_si_estado_actual(
        self, document_id: int, evento: EventoEstado, estado_esperado: str | None
    ) -> EstadoDocumento | None:
        """Agrega el evento solo si el estado aún coincide con el leído por el servicio."""
        evento_json = evento.model_dump(mode="json")
        filtro: dict = {"document_id": document_id}
        upsert = estado_esperado is None
        if upsert:
            filtro["estado_actual"] = {"$exists": False}
        else:
            filtro["estado_actual"] = estado_esperado

        try:
            payload = self.collection.find_one_and_update(
                filtro,
                {
                    "$set": {"estado_actual": evento.estado, "updated_at": evento_json["timestamp"]},
                    "$push": {"historial": evento_json},
                    "$setOnInsert": {"document_id": document_id},
                },
                upsert=upsert,
                return_document=ReturnDocument.AFTER,
            )
        except DuplicateKeyError:
            # Otra réplica creó el estado inicial mientras esta solicitud intentaba insertarlo.
            return None
        return self._deserialize(payload)

    def get_all(self, skip: int = 0, limit: int = 50) -> list[EstadoDocumento]:
        cursor = self.collection.find().skip(skip).limit(limit)
        return [self._deserialize(p) for p in cursor]

    def _deserialize(self, payload: dict | None) -> EstadoDocumento | None:
        if payload is None:
            return None
        payload = {k: v for k, v in payload.items() if k != "_id"}
        return EstadoDocumento(**payload)
