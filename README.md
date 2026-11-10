# notificaciones-service

Microservicio de **estado y notificaciones**, cuarto de la migración del monolito
`El-Destripador-de-PDFs` hacia microservicios.

Lleva el registro de en qué etapa del flujo está cada documento
(`subido → extraido → resumido → notificado`, o `error`). Cada microservicio le
informa sus avances, y este servicio guarda el estado actual y un historial
completo de eventos por documento.

## Arquitectura (capas)

```
App/
├── api/Routes/estado.py          # POST /estados, GET /estados/{id}, GET /estados
├── api/exception_handlers.py     # excepciones de dominio -> HTTP
├── services/estado_service.py    # valida transiciones, arma historial
├── repositories/estado_repository.py  # acceso a MongoDB (upsert por document_id)
├── models/ · schemas/            # dominio y DTOs
├── utils/database.py             # conexión Mongo / mongomock
└── config/settings.py
test/                              # 9 tests (unitarios + integración)
```

## Estados del flujo

`subido`, `extraido`, `resumido`, `notificado`, `error`. Cualquier otro valor se
rechaza con HTTP 400.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/estados` | Registra un estado: `{"document_id": N, "estado": "extraido", "detalle": "..."}` |
| GET | `/api/v1/estados/{document_id}` | Estado actual + historial de un documento |
| GET | `/api/v1/estados` | Lista los estados de todos los documentos (paginado) |
| GET | `/health` | Health check |

## Errores

| Situación | HTTP |
|---|---|
| Estado no válido | 400 |
| Documento sin registro de estado | 404 |

## Configuración

Copiar `.env.example` a `.env`. Para desarrollo sin Mongo real:
`DATABASE_URL=mongomock://localhost`.

## Correr los tests

Con **uv** (recomendado, más rápido y con `uv.lock` para versiones reproducibles):

```bash
uv sync --extra dev
uv run --extra dev pytest test/ -v
```

O con pip tradicional:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest test/ -v
```

## Escaneo de seguridad

El workflow `Security scan` audita las dependencias de runtime fijadas en
`uv.lock` y construye/escanea la imagen Docker con Trivy. Se ejecuta en cada PR,
push a `main`/`master`, semanalmente (lunes 06:00 UTC) y manualmente desde
GitHub Actions. Un hallazgo HIGH o CRITICAL falla el job; los detalles quedan
visibles en el log del workflow. También verifica que la imagen se ejecute como
un usuario distinto de root.

## Stack

Python 3.12+ · FastAPI · MongoDB (pymongo) / mongomock · pytest
