"""Pruebas de integración de la API de Notificaciones, con mongomock."""

import os

os.environ.setdefault("DATABASE_URL", "mongomock://localhost")

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    from App.main import app
    from App.utils.database import get_client, settings

    get_client().drop_database(settings.database_name)
    return TestClient(app)


def test_flujo_completo_de_estados(client):
    # Registrar avance del documento por las etapas del flujo
    r1 = client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})
    assert r1.status_code == 200

    r2 = client.post("/api/v1/estados", json={"document_id": 1, "estado": "extraido", "detalle": "1500 chars"})
    assert r2.status_code == 200

    r3 = client.post("/api/v1/estados", json={"document_id": 1, "estado": "resumido"})
    assert r3.status_code == 200
    assert r3.json()["estado_actual"] == "resumido"
    assert len(r3.json()["historial"]) == 3

    r4 = client.post("/api/v1/estados", json={"document_id": 1, "estado": "notificado"})
    assert r4.status_code == 200
    assert r4.json()["estado_actual"] == "notificado"
    assert len(r4.json()["historial"]) == 4

    # Consultar el estado actual
    r5 = client.get("/api/v1/estados/1")
    assert r5.status_code == 200
    assert r5.json()["estado_actual"] == "notificado"


def test_estado_invalido_devuelve_400(client):
    r = client.post("/api/v1/estados", json={"document_id": 1, "estado": "inexistente"})
    assert r.status_code == 400


def test_transicion_fuera_de_orden_devuelve_409_y_no_cambia_historial(client):
    client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})

    r = client.post("/api/v1/estados", json={"document_id": 1, "estado": "resumido"})
    actual = client.get("/api/v1/estados/1")

    assert r.status_code == 409
    assert actual.json()["estado_actual"] == "subido"
    assert [evento["estado"] for evento in actual.json()["historial"]] == ["subido"]


def test_repetir_estado_actual_no_duplica_historial(client):
    client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})

    r = client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})

    assert r.status_code == 200
    assert [evento["estado"] for evento in r.json()["historial"]] == ["subido"]


def test_error_y_reintento_pueden_reiniciar_el_flujo(client):
    client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})
    error = client.post("/api/v1/estados", json={"document_id": 1, "estado": "error"})
    reintento = client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})

    assert error.status_code == 200
    assert reintento.status_code == 200
    assert [evento["estado"] for evento in reintento.json()["historial"]] == [
        "subido",
        "error",
        "subido",
    ]


def test_documento_sin_estado_devuelve_404(client):
    r = client.get("/api/v1/estados/999999")
    assert r.status_code == 404


def test_listar_estados(client):
    client.post("/api/v1/estados", json={"document_id": 1, "estado": "subido"})
    client.post("/api/v1/estados", json={"document_id": 2, "estado": "subido"})
    r = client.get("/api/v1/estados")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_health_check(client):
    assert client.get("/health").status_code == 200
