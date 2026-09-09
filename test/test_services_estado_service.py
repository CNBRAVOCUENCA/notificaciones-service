"""Pruebas unitarias para EstadoService."""

import pytest

from App.exceptions import DocumentoNoEncontradoError, EstadoInvalidoError
from App.repositories.estado_repository import EstadoRepository
from App.services.estado_service import EstadoService


@pytest.fixture
def repo(fake_db):
    return EstadoRepository(fake_db)


@pytest.fixture
def service(repo):
    return EstadoService(repo)


def test_actualizar_estado_nuevo_documento(service, fake_db):
    fake_db._cols["estados"].find_one.return_value = None
    estado = service.actualizar_estado(1, "subido", "archivo recibido")
    assert estado.document_id == 1
    assert estado.estado_actual == "subido"
    assert len(estado.historial) == 1
    fake_db._cols["estados"].update_one.assert_called_once()


def test_actualizar_estado_agrega_al_historial(service, fake_db):
    fake_db._cols["estados"].find_one.return_value = {
        "document_id": 1, "estado_actual": "subido",
        "historial": [{"estado": "subido", "timestamp": "2026-01-01T00:00:00+00:00", "detalle": ""}],
        "updated_at": "2026-01-01T00:00:00+00:00",
    }
    estado = service.actualizar_estado(1, "extraido", "texto extraído")
    assert estado.estado_actual == "extraido"
    assert len(estado.historial) == 2


def test_actualizar_estado_invalido(service):
    with pytest.raises(EstadoInvalidoError):
        service.actualizar_estado(1, "volando", "")


def test_obtener_estado_inexistente(service, fake_db):
    fake_db._cols["estados"].find_one.return_value = None
    with pytest.raises(DocumentoNoEncontradoError):
        service.obtener_estado(999)
