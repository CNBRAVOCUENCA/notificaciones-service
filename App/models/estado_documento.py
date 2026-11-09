"""Modelo de dominio para el estado de un documento en el flujo."""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

# Estados válidos del flujo, en orden
ESTADOS_VALIDOS = ["subido", "extraido", "resumido", "notificado", "error"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class EventoEstado(BaseModel):
    """Un cambio de estado puntual, con su marca de tiempo."""
    estado: str
    timestamp: datetime = Field(default_factory=_utc_now)
    detalle: str = ""


class EstadoDocumento(BaseModel):
    """Estado actual de un documento y su historial de eventos."""
    document_id: int
    estado_actual: str
    historial: list[EventoEstado] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=_utc_now)
