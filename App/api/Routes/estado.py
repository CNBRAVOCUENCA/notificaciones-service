"""Rutas REST del microservicio de Notificaciones / Estado."""

from typing import List

from fastapi import APIRouter, Depends
from pymongo.database import Database

from App.repositories.estado_repository import EstadoRepository
from App.schemas.estado import ActualizarEstadoRequest, EstadoResponse
from App.services.estado_service import EstadoService
from App.utils.database import get_db

router = APIRouter(prefix="/estados", tags=["estados"])


def _get_service(db: Database = Depends(get_db)) -> EstadoService:
    return EstadoService(EstadoRepository(db))


@router.post("", response_model=EstadoResponse)
async def actualizar_estado(payload: ActualizarEstadoRequest, service: EstadoService = Depends(_get_service)) -> EstadoResponse:
    """Registra un nuevo estado para un documento (subido/extraido/resumido/...)."""
    estado = service.actualizar_estado(payload.document_id, payload.estado, payload.detalle)
    return EstadoResponse(**estado.model_dump())


@router.get("/{document_id}", response_model=EstadoResponse)
async def obtener_estado(document_id: int, service: EstadoService = Depends(_get_service)) -> EstadoResponse:
    """Devuelve el estado actual y el historial de un documento."""
    estado = service.obtener_estado(document_id)
    return EstadoResponse(**estado.model_dump())


@router.get("", response_model=List[EstadoResponse])
async def listar_estados(skip: int = 0, limit: int = 50, service: EstadoService = Depends(_get_service)) -> List[EstadoResponse]:
    """Lista los estados de todos los documentos (paginado)."""
    return [EstadoResponse(**e.model_dump()) for e in service.listar(skip, limit)]
