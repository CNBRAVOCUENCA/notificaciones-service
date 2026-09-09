"""Conexión a MongoDB. Soporta `mongomock://` para tests/desarrollo local."""

from functools import lru_cache

from pymongo import ASCENDING, MongoClient
from pymongo.database import Database

from App.config.settings import settings


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    if settings.database_url.startswith("mongomock://"):
        import mongomock
        return mongomock.MongoClient()
    return MongoClient(settings.database_url, serverSelectionTimeoutMS=settings.database_timeout_ms, connect=False)


def get_database() -> Database:
    return get_client()[settings.database_name]


def get_db() -> Database:
    return get_database()


def ensure_indexes() -> None:
    db = get_database()
    db["estados"].create_index([("document_id", ASCENDING)], unique=True, name="idx_estados_document_id")
