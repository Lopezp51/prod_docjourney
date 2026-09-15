"""
Router de Verificação de Saúde e Métricas da Aplicação.
"""

from fastapi import APIRouter, Depends
from microservico.api.schemas import HealthResponse
from microservico.api.dependencies import get_db_manager, get_rabbitmq_client, DatabaseManager
from microservico.notifier.rabbitmq_client import RabbitMQClient

router = APIRouter(tags=["Saúde e Diagnóstico"])


@router.get("/health", response_model=HealthResponse, summary="Verifica a integridade do microsserviço")
def check_health(
    db: DatabaseManager = Depends(get_db_manager),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Retorna o status de conexão com o banco de dados (PostgreSQL/SQLite)
    e com o broker RabbitMQ (ou fallback em memória).
    """
    db_status = "connected"
    try:
        db.fetch_one("SELECT 1")
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    rmq_status = "connected" if rabbitmq._is_live_connection else "mock_queue_active"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        database=db_status,
        rabbitmq=rmq_status,
        version="2.0.0"
    )
