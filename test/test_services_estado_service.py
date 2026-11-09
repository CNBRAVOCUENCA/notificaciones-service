"""Pruebas unitarias para EstadoService."""

import mongomock
import pytest
from App.exceptions import DocumentoNoEncontradoError, EstadoInvalidoError
from App.repositories.estado_repository import EstadoRepository
from App.services.estado_service import EstadoService


@pytest.fixture
def repo():
    return EstadoRepository(mongomock.MongoClient()["test_estados"])


@pytest.fixture
def service(repo):
    return EstadoService(repo)


def test_actualizar_estado_nuevo_documento(service):
    estado = service.actualizar_estado(1, "subido", "archivo recibido")
    assert estado.document_id == 1
    assert estado.estado_actual == "subido"
    assert len(estado.historial) == 1


def test_actualizar_estado_agrega_al_historial(service):
    service.actualizar_estado(1, "subido", "archivo recibido")
    estado = service.actualizar_estado(1, "extraido", "texto extraído")
    assert estado.estado_actual == "extraido"
    assert [e.estado for e in estado.historial] == ["subido", "extraido"]


def test_actualizar_estado_invalido(service):
    with pytest.raises(EstadoInvalidoError):
        service.actualizar_estado(1, "volando", "")


def test_obtener_estado_inexistente(service):
    with pytest.raises(DocumentoNoEncontradoError):
        service.obtener_estado(999)
