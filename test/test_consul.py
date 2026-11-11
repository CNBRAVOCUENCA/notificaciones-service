"""Pruebas del registro y ciclo de vida de Consul."""

import asyncio
import json
from unittest.mock import AsyncMock

import httpx
import pytest
from App.config.settings import Settings
from App.services.consul import ConsulServiceRegistration
from fastapi import FastAPI


def make_settings(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)


def _registrar_pedido(requests):
    """Guarda los pedidos de alta y baja; la consulta de registros viejos responde vacía."""

    def handler(request):
        if request.method == "GET" and request.url.path == "/v1/agent/services":
            return httpx.Response(200, json={})
        requests.append(request)
        return httpx.Response(200)

    return handler


def test_registration_payload_and_auth(monkeypatch):
    requests = []
    transport = httpx.MockTransport(_registrar_pedido(requests))
    config = make_settings(
        consul_http_addr="http://consul:8500",
        consul_http_token="secret-token",
        consul_service_name="notifications",
        consul_service_port=8123,
        consul_service_tags="traefik.enable=true, route=api,",
    )
    monkeypatch.setattr("App.services.consul.socket.gethostname", lambda: "instance-1")
    monkeypatch.setattr("App.services.consul._service_address", lambda _addr: "172.20.0.4")
    registration = ConsulServiceRegistration(config)
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "App.services.consul.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    async def register_and_deregister():
        await registration.start()
        await registration.stop()

    asyncio.run(register_and_deregister())

    request = requests[0]
    assert request.method == "PUT"
    assert str(request.url) == "http://consul:8500/v1/agent/service/register"
    assert request.headers["X-Consul-Token"] == "secret-token"
    payload = json.loads(request.content)
    assert payload == {
        "name": "notifications",
        "id": "notifications-instance-1",
        "address": "172.20.0.4",
        "port": 8123,
        "tags": ["traefik.enable=true", "route=api"],
        "check": {
            "http": "http://172.20.0.4:8123/health",
            "interval": "10s",
            "timeout": "2s",
            "DeregisterCriticalServiceAfter": "1m",
        },
    }


def test_registration_uses_name_default_and_deregisters(monkeypatch):
    requests = []
    transport = httpx.MockTransport(_registrar_pedido(requests))
    config = make_settings(consul_http_addr="http://consul:8500", app_name="app")
    monkeypatch.setattr("App.services.consul.socket.gethostname", lambda: "runtime-host")
    monkeypatch.setattr("App.services.consul._service_address", lambda _addr: "10.0.0.5")
    registration = ConsulServiceRegistration(config)
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "App.services.consul.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=transport, **kwargs),
    )

    async def run_lifecycle():
        await registration.start()
        await registration.stop()

    asyncio.run(run_lifecycle())

    assert requests[0].headers.get("X-Consul-Token") is None
    assert requests[1].method == "PUT"
    assert str(requests[1].url) == (
        "http://consul:8500/v1/agent/service/deregister/app-runtime-host"
    )


def test_registration_disabled_without_consul_address():
    registration = ConsulServiceRegistration(make_settings(consul_http_addr=""))
    asyncio.run(registration.start())
    asyncio.run(registration.stop())
    assert registration._client is None


def test_dockerfile_runs_as_non_root():
    from pathlib import Path

    dockerfile = Path(__file__).parents[1].joinpath("Dockerfile").read_text()
    user_directives = [line.split(maxsplit=1)[1] for line in dockerfile.splitlines() if line.startswith("USER ")]

    assert user_directives
    assert user_directives[-1].lower() not in {"root", "0", "root:root", "0:0"}


def test_registration_failure_is_sanitized_and_closes_client(monkeypatch):
    config = make_settings(consul_http_addr="http://consul:8500", consul_http_token="never-log-this")
    client = AsyncMock()
    client.put.side_effect = httpx.ConnectError("never-log-this")
    monkeypatch.setattr("App.services.consul._service_address", lambda _addr: "172.20.0.4")
    monkeypatch.setattr("App.services.consul.httpx.AsyncClient", lambda **_kwargs: client)

    with pytest.raises(RuntimeError, match="Consul service registration failed") as error:
        asyncio.run(ConsulServiceRegistration(config).start())

    assert "never-log-this" not in str(error.value)
    client.aclose.assert_awaited_once()


def test_shutdown_errors_are_logged_without_token(monkeypatch, caplog):
    config = make_settings(
        consul_http_addr="http://consul:8500",
        consul_http_token="never-log-this",
    )
    client = AsyncMock()
    client.put.side_effect = httpx.ConnectError("never-log-this")
    registration = ConsulServiceRegistration(config)
    registration._client = client
    registration._service_id = "service-host"
    monkeypatch.setattr("App.services.consul.socket.gethostname", lambda: "host")

    asyncio.run(registration.stop())

    assert "deregistration failed" in caplog.text
    assert "never-log-this" not in caplog.text
    client.aclose.assert_awaited_once()


def test_fastapi_lifespan_registers_then_deregisters(monkeypatch):
    from App import main

    registration = AsyncMock()
    monkeypatch.setattr(main, "consul_registration", registration)
    monkeypatch.setattr(main, "ensure_indexes", lambda: None)
    app = FastAPI()

    async def run_lifecycle():
        async with main.lifespan(app):
            registration.start.assert_awaited_once()
            registration.stop.assert_not_awaited()
        registration.stop.assert_awaited_once()

    asyncio.run(run_lifecycle())


def test_al_registrar_da_de_baja_registros_viejos_con_la_misma_ip(monkeypatch):
    """Docker reutiliza IP: un registro viejo con la misma IP:puerto se borra antes del alta."""
    pedidos = []

    def handler(request):
        pedidos.append((request.method, request.url.path))
        if request.url.path == "/v1/agent/services":
            return httpx.Response(
                200,
                json={
                    "viejo-del-mismo-servicio": {"Address": "10.0.0.5", "Port": 8000},
                    "otro-servicio-misma-ip": {"Address": "10.0.0.5", "Port": 8000},
                    "otra-instancia-valida": {"Address": "10.0.0.9", "Port": 8000},
                    "notificaciones-host": {"Address": "10.0.0.5", "Port": 8000},
                },
            )
        return httpx.Response(200)

    config = make_settings(consul_http_addr="http://consul:8500", consul_service_name="notificaciones")
    monkeypatch.setattr("App.services.consul.socket.gethostname", lambda: "host")
    monkeypatch.setattr("App.services.consul._service_address", lambda _addr: "10.0.0.5")
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "App.services.consul.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    registration = ConsulServiceRegistration(config)
    asyncio.run(registration.start())

    bajas = [path for method, path in pedidos if "deregister" in path]
    assert bajas == [
        "/v1/agent/service/deregister/viejo-del-mismo-servicio",
        "/v1/agent/service/deregister/otro-servicio-misma-ip",
    ]
    assert pedidos[-1] == ("PUT", "/v1/agent/service/register")


def test_si_consul_falla_al_limpiar_igual_se_registra(monkeypatch):
    pedidos = []

    def handler(request):
        pedidos.append(request.url.path)
        if request.url.path == "/v1/agent/services":
            return httpx.Response(500)
        return httpx.Response(200)

    config = make_settings(consul_http_addr="http://consul:8500")
    monkeypatch.setattr("App.services.consul._service_address", lambda _addr: "10.0.0.5")
    original_client = httpx.AsyncClient
    monkeypatch.setattr(
        "App.services.consul.httpx.AsyncClient",
        lambda **kwargs: original_client(transport=httpx.MockTransport(handler), **kwargs),
    )
    asyncio.run(ConsulServiceRegistration(config).start())
    assert pedidos[-1] == "/v1/agent/service/register"
