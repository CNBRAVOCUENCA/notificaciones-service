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
rechaza con HTTP 400. La primera actualización debe ser `subido`; la progresión
normal es `subido → extraido → resumido → notificado`. Se puede registrar
`error` desde cualquier etapa, y un documento en `error` puede reiniciar el
flujo con `subido` para permitir reintentos. Repetir el estado actual es
idempotente y no agrega entradas al historial. Las transiciones fuera de orden
se rechazan sin modificar el estado ni el historial.

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
| Transición fuera de orden o conflicto concurrente | 409 |
| Documento sin registro de estado | 404 |

## Configuración

Copiar `.env.example` a `.env`. Para desarrollo sin Mongo real:
`DATABASE_URL=mongomock://localhost`.

### Usuario de ejecución en Docker

La imagen ejecuta Uvicorn como el usuario y grupo sin privilegios `app`. El
servicio no necesita escribir en `/app` ni en otros directorios locales; los
logs se envían a stdout y la persistencia se realiza en MongoDB.

### Consul y Traefik

El registro en Consul es opcional: con `CONSUL_HTTP_ADDR` vacío (valor
predeterminado) el servicio funciona sin descubrimiento. Para el despliegue,
configurar la dirección HTTP del agente, por ejemplo
`CONSUL_HTTP_ADDR=http://consul:8500`. El servicio se registra al iniciar y se
da de baja al apagar; Consul consulta `GET /health` cada 10 segundos y elimina
el registro si permanece crítico durante un minuto. Si el registro configurado
falla, la aplicación no inicia.

`CONSUL_HTTP_TOKEN` es opcional y se envía al agente como token HTTP, nunca se
incluye en los logs. `CONSUL_SERVICE_NAME` toma `APP_NAME` por defecto,
`CONSUL_SERVICE_PORT` es 8000 y `CONSUL_SERVICE_TAGS` acepta etiquetas
separadas por comas (por ejemplo `traefik.enable=true,traefik.http.routers.notificaciones.rule=PathPrefix(/api/v1)`).
`CONSUL_SERVICE_ADDRESS` permite definir la IP anunciada; si se omite, se
determina la IP de red de esta instancia hacia el agente, para que las
instancias replicadas se registren por separado y Traefik pueda alcanzarlas.

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
GitHub Actions. La política es: **falla el job cualquier hallazgo HIGH o CRITICAL que tenga
parche disponible** (`ignore-unfixed: true`). Los HIGH/CRITICAL sin parche de la
imagen base (paquetes de Debian en estado *affected*, sin versión corregida)
**se siguen mostrando** en la tabla del log, pero no bloquean: no hay acción
posible desde este repo hasta que Debian publique el arreglo, y en ese momento el
escaneo semanal empieza a fallar y obliga a reconstruir la imagen. No se usan
`.trivyignore` ni otros filtros. Los detalles quedan visibles en el log del workflow. También verifica que la imagen se ejecute como
un usuario distinto de root.

## Stack

Python 3.12+ · FastAPI · MongoDB (pymongo) / mongomock · pytest
