"""Configuración del microservicio, vía variables de entorno."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "notificaciones-service"
    app_version: str = "0.1.0"
    debug: bool = False

    database_url: str = "mongodb://localhost:27017"
    database_name: str = "notificaciones_service"
    database_timeout_ms: int = 5000
    api_v1_prefix: str = "/api/v1"

    consul_http_addr: str = ""
    consul_http_token: str | None = None
    consul_service_name: str | None = None
    consul_service_port: int = Field(default=8000, gt=0, le=65535)
    consul_service_tags: str = ""
    consul_service_address: str | None = None


settings = Settings()
