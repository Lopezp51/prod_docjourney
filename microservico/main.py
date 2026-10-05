"""
Ponto de Entrada Principal da Aplicação FastAPI do Microsserviço DocJourney.
Configura middlewares, ciclo de vida (lifespan), documentação Swagger OpenAPI e roteamento.
"""

import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from microservico.logging_config import logger
from microservico.config import config
from microservico.api.dependencies import get_db_manager
from microservico.api.routers import health, journeys, envelopes, maintenance



@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Ciclo de vida da aplicação FastAPI:
    1. Inicializa o schema do banco de dados (idempotente).
    2. Acopla o consumidor RabbitMQ (Worker) em thread paralela caso ENABLE_EMBEDDED_WORKER esteja ativo.
    """
    logger.info("--> Iniciando DocJourney Backend & Maintenance API...")

    # 1. Conexão com o banco e inicialização de tabelas
    try:
        db = get_db_manager()
        logger.info(f"Banco de dados inicializado com sucesso (Modo SQLite: {db.use_sqlite}).")
    except Exception as e:
        logger.error(f"Aviso ao inicializar banco: {e}")

    # 2. Inicialização do Consumidor RabbitMQ integrado em background (single terminal mode)
    worker_thread = None
    stop_event = None
    if config.ENABLE_EMBEDDED_WORKER:
        try:
            from microservico.worker import start_worker_thread
            logger.info("--> [Lifespan] Disparando Consumidor RabbitMQ em background thread (Embedded Worker)...")
            worker_thread, stop_event = start_worker_thread(interval_seconds=1.5)
            logger.info("--> [Lifespan] Consumidor RabbitMQ integrado rodando com sucesso!")
        except Exception as e:
            logger.warning(f"--> [Lifespan] Não foi possível iniciar worker integrado: {e}")

    yield

    # 3. Finalização graciosa do consumidor
    if stop_event:
        logger.info("--> [Lifespan] Encerrando Consumidor RabbitMQ integrado...")
        stop_event.set()
        if worker_thread:
            worker_thread.join(timeout=2.0)

    logger.info("--> Finalizando DocJourney Backend & Maintenance API.")


app = FastAPI(
    title="DocJourney Backend & Maintenance API",
    description=(
        "Microsserviço central de governança, persistência relacional (PostgreSQL/SQLite) "
        "e mensageria RabbitMQ para a esteira de assinaturas eletrônicas. "
        "Elimina o uso de queries SQL manuais no banco através de endpoints dedicados "
        "à operação e manutenção da esteira."
    ),
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Habilita CORS para integração com painéis web e ferramentas corporativas
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Middleware de observabilidade para log estruturado de requisições HTTP."""
    start_time = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start_time) * 1000

    # Log detalhado apenas para endpoints de negócio ou se houver erro
    if request.url.path != "/health" or response.status_code >= 400:
        logger.info(
            f"HTTP {request.method} {request.url.path} | Status: {response.status_code} | Tempo: {duration_ms:.2f}ms"
        )
    return response


# Registro dos Routers da API
app.include_router(health.router)
app.include_router(journeys.router)
app.include_router(envelopes.router)
app.include_router(maintenance.router)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("microservico.main:app", host="0.0.0.0", port=8000, reload=True)
