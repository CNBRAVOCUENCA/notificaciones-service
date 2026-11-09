"""Schemas (DTOs) de la API de Notificaciones / Estado."""

from datetime import datetime

from pydantic import BaseModel


class ActualizarEstadoRequest(BaseModel):
    document_id: int
    estado: str
    detalle: str = ""


class EventoResponse(BaseModel):
    estado: str
    timestamp: datetime
    detalle: str


class EstadoResponse(BaseModel):
    document_id: int
    estado_actual: str
    historial: list[EventoResponse]
    updated_at: datetime
