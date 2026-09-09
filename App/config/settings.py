"""Configuración del microservicio, vía variables de entorno."""

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


settings = Settings()
