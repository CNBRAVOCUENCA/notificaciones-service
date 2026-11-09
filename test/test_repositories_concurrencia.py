"""El historial de estados no debe perder eventos con escrituras concurrentes.

Varias réplicas (o la compensación de la Saga) pueden notificar el mismo
documento casi a la vez. Se simula que otra réplica agrega un evento justo
antes de nuestra escritura: ese evento tiene que seguir estando después.
"""

import mongomock
import pytest
from App.repositories.estado_repository import EstadoRepository
from App.services.estado_service import EstadoService


class _ColeccionConOtraReplica:
    """Envuelve la colección e inserta un evento ajeno antes de cada escritura."""

    def __init__(self, real):
        self._real = real
        self.activo = False

    def _otra_replica_escribe(self, filtro):
        if self.activo:
            self.activo = False
            self._real.update_one(filtro, {"$push": {"historial": {
                "estado": "extraido", "timestamp": "2026-01-01T00:00:00+00:00", "detalle": "otra réplica",
            }}})

    def update_one(self, filtro, *args, **kwargs):
        self._otra_replica_escribe(filtro)
        return self._real.update_one(filtro, *args, **kwargs)

    def find_one_and_update(self, filtro, *args, **kwargs):
        self._otra_replica_escribe(filtro)
        return self._real.find_one_and_update(filtro, *args, **kwargs)

    def __getattr__(self, nombre):
        return getattr(self._real, nombre)


@pytest.fixture
def entorno():
    db = mongomock.MongoClient()["test_estados"]
    repo = EstadoRepository(db)
    coleccion = _ColeccionConOtraReplica(db["estados"])
    repo.collection = coleccion
    return EstadoService(repo), coleccion


def test_no_se_pierden_eventos_de_otra_replica(entorno):
    service, coleccion = entorno
    service.actualizar_estado(1, "subido")

    coleccion.activo = True  # otra réplica escribe justo antes que nosotros
    estado = service.actualizar_estado(1, "resumido")

    detalles = [e.detalle for e in service.obtener_estado(1).historial]
    assert "otra réplica" in detalles
    assert len(detalles) == 3
    assert estado.estado_actual == "resumido"
    assert len(estado.historial) == 3


def test_primer_evento_crea_el_registro(entorno):
    service, _ = entorno
    estado = service.actualizar_estado(5, "subido", "inicio")
    assert estado.document_id == 5
    assert [e.estado for e in estado.historial] == ["subido"]
