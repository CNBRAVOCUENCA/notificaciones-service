"""Pruebas unitarias para EstadoService."""

import mongomock
import pytest
from App.exceptions import (
    DocumentoNoEncontradoError,
    EstadoInvalidoError,
    TransicionEstadoInvalidaError,
)
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


def test_actualizar_estado_permite_la_secuencia_completa(service):
    estado = service.actualizar_estado(1, "subido")
    estado = service.actualizar_estado(1, "extraido")
    estado = service.actualizar_estado(1, "resumido")
    estado = service.actualizar_estado(1, "notificado")

    assert estado.estado_actual == "notificado"
    assert [evento.estado for evento in estado.historial] == [
        "subido",
        "extraido",
        "resumido",
        "notificado",
    ]


def test_rechaza_estado_inicial_distinto_de_subido_sin_agregar_historial(service):
    with pytest.raises(TransicionEstadoInvalidaError):
        service.actualizar_estado(1, "extraido")

    assert service.repository.get_by_document_id(1) is None


@pytest.mark.parametrize(
    ("estados_anteriores", "siguiente"),
    [
        (["subido"], "resumido"),
        (["subido", "extraido"], "notificado"),
    ],
)
def test_rechaza_saltos_de_etapa_sin_alterar_historial(service, estados_anteriores, siguiente):
    for estado in estados_anteriores:
        service.actualizar_estado(1, estado)
    historial_antes = service.obtener_estado(1).historial

    with pytest.raises(TransicionEstadoInvalidaError):
        service.actualizar_estado(1, siguiente)

    assert service.obtener_estado(1).historial == historial_antes


@pytest.mark.parametrize(
    ("estado_actual", "secuencia"),
    [
        ("subido", ["subido"]),
        ("extraido", ["subido", "extraido"]),
        ("resumido", ["subido", "extraido", "resumido"]),
        ("notificado", ["subido", "extraido", "resumido", "notificado"]),
    ],
)
def test_error_es_permitido_desde_cualquier_etapa(service, estado_actual, secuencia):
    for estado in secuencia:
        service.actualizar_estado(1, estado)

    estado = service.actualizar_estado(1, "error", "falló el procesamiento")

    assert estado.estado_actual == "error"
    assert [evento.estado for evento in estado.historial] == [*secuencia, "error"]


def test_reintento_puede_reiniciar_desde_error(service):
    service.actualizar_estado(1, "subido")
    service.actualizar_estado(1, "extraido")
    service.actualizar_estado(1, "error", "falló el resumen")

    estado = service.actualizar_estado(1, "subido", "reintento")

    assert estado.estado_actual == "subido"
    assert [evento.estado for evento in estado.historial] == ["subido", "extraido", "error", "subido"]


def test_repetir_estado_actual_es_idempotente_y_no_duplica_historial(service):
    service.actualizar_estado(1, "subido", "archivo recibido")

    estado = service.actualizar_estado(1, "subido", "reintento de notificación")

    assert estado.estado_actual == "subido"
    assert [evento.estado for evento in estado.historial] == ["subido"]
    assert estado.historial[0].detalle == "archivo recibido"


def test_actualizar_estado_invalido(service):
    with pytest.raises(EstadoInvalidoError):
        service.actualizar_estado(1, "volando", "")


def test_obtener_estado_inexistente(service):
    with pytest.raises(DocumentoNoEncontradoError):
        service.obtener_estado(999)
