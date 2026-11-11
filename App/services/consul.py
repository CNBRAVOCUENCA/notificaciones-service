"""Registro de instancias del servicio en el agente local de Consul."""

import contextlib
import logging
import socket

import httpx

from App.config.settings import Settings, settings

logger = logging.getLogger(__name__)


def _service_address(consul_addr: str) -> str:
    consul_url = httpx.URL(consul_addr)
    if not consul_url.host:
        raise ValueError("CONSUL_HTTP_ADDR must contain a host")

    port = consul_url.port or (8501 if consul_url.scheme == "https" else 8500)
    for family, socktype, protocol, _, address_info in socket.getaddrinfo(
        consul_url.host, port, type=socket.SOCK_DGRAM
    ):
        try:
            with socket.socket(family, socktype, protocol) as sock:
                sock.connect(address_info)
                return sock.getsockname()[0]
        except OSError:
            continue
    raise OSError("Unable to determine a routable service address")


def _health_url(address: str, port: int) -> str:
    host = f"[{address}]" if ":" in address and not address.startswith("[") else address
    return f"http://{host}:{port}/health"


class ConsulServiceRegistration:
    def __init__(self, config: Settings = settings) -> None:
        self._config = config
        self._client: httpx.AsyncClient | None = None
        self._service_id: str | None = None

    async def start(self) -> None:
        consul_addr = self._config.consul_http_addr.strip()
        if not consul_addr:
            return

        try:
            service_name = self._config.consul_service_name or self._config.app_name
            service_id = f"{service_name}-{socket.gethostname()}"
            address_override = (self._config.consul_service_address or "").strip()
            address = address_override or _service_address(consul_addr)
            tags = [tag.strip() for tag in self._config.consul_service_tags.split(",") if tag.strip()]
            headers = {}
            if self._config.consul_http_token:
                headers["X-Consul-Token"] = self._config.consul_http_token

            client = httpx.AsyncClient(timeout=5.0, headers=headers)
            self._client = client
            response = await client.put(
                f"{consul_addr.rstrip('/')}/v1/agent/service/register",
                json={
                    "name": service_name,
                    "id": service_id,
                    "address": address,
                    "port": self._config.consul_service_port,
                    "tags": tags,
                    "check": {
                        "http": _health_url(address, self._config.consul_service_port),
                        "interval": "10s",
                        "timeout": "2s",
                        "DeregisterCriticalServiceAfter": "1m",
                    },
                },
            )
            response.raise_for_status()
            self._service_id = service_id
        except Exception as exc:
            if self._client is not None:
                with contextlib.suppress(Exception):
                    await self._client.aclose()
                self._client = None
            logger.error("Consul service registration failed (%s)", type(exc).__name__)
            raise RuntimeError("Consul service registration failed") from None

    async def stop(self) -> None:
        if self._client is None or self._service_id is None:
            return

        client = self._client
        service_id = self._service_id
        self._client = None
        self._service_id = None
        try:
            response = await client.put(
                f"{self._config.consul_http_addr.rstrip('/')}/v1/agent/service/deregister/{service_id}"
            )
            response.raise_for_status()
        except Exception as exc:
            logger.warning("Consul service deregistration failed (%s)", type(exc).__name__)
        finally:
            try:
                await client.aclose()
            except Exception as exc:
                logger.warning("Consul client shutdown failed (%s)", type(exc).__name__)
