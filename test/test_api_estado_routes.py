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

    # Consultar el estado actual
    r4 = client.get("/api/v1/estados/1")
    assert r4.status_code == 200
    assert r4.json()["estado_actual"] == "resumido"


def test_estado_invalido_devuelve_400(client):
    r = client.post("/api/v1/estados", json={"document_id": 1, "estado": "inexistente"})
    assert r.status_code == 400


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
