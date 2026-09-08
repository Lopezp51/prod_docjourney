"""
Ponto de Entrada Principal da Automação RPA (DocJourney Automation).
Executa o processamento de tarefas vindas do MongoDB/Fluid e gera retornos formatados para a esteira.
Nomes de funções, parâmetros e variáveis 100% em inglês com docstrings explicativas em português.
"""

import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

from automacao.domain.exceptions import BaseFlowException
from automacao.controllers.orchestrator_ctr import OrchestratorController
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.config import config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RPA_Automation")


@contextmanager
def automation_context(use_sqlite: bool = True):
    """
    Gerenciador de contexto para inicialização e finalização segura do ambiente de execução RPA.

    Garante a verificação e carga do esquema de banco (PROD_schema.sql) e dos processos básicos.

    Parâmetros:
        use_sqlite (bool): Se True, utiliza banco em memória. Se False, conecta ao PostgreSQL de produção.

    Yields:
        DatabaseManager: Instância configurada e inicializada do gerenciador de banco.
    """
    logger.info("Iniciando contexto de execução da automação RPA.")
    if use_sqlite:
        db_manager = DatabaseManager(use_sqlite=True)
    else:
        dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
        db_manager = DatabaseManager(dsn=dsn, use_sqlite=False)

    initialize_database_if_empty(db_manager)
    try:
        yield db_manager
    finally:
        logger.info("Finalizando contexto de execução da automação RPA.")


def run_automation_task(
    task_payload: Dict[str, Any],
    use_sqlite: bool = True,
    db_manager: Optional[DatabaseManager] = None,
    openapi_client: Optional[Any] = None,
    rabbitmq_client: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Função principal de processamento de uma tarefa recebida da esteira Fluid / MongoDB.

    Captura de forma unificada as exceções do tipo BaseFlowException e gera o parecer
    formatado em HTML para devolução imediata à esteira em caso de pendências.

    Parâmetros:
        task_payload (Dict[str, Any]): Metadados e documentos da tarefa do processo.
        use_sqlite (bool): Quando True, utiliza banco em memória para testes (padrão: True).
        db_manager (Optional[DatabaseManager]): Conexão de banco pré-existente (opcional).
        openapi_client (Optional[Any]): Instância customizada do cliente OpenAPI v2 (opcional).
        rabbitmq_client (Optional[Any]): Cliente persistente RabbitMQ para eventos (opcional).

    Retorno:
        Dict[str, Any]: Dicionário com resultado da execução ('SUCESSO', 'ERRO_FLUXO' ou 'ERRO_INESPERADO').
    """
    if db_manager is None:
        if use_sqlite:
            db_mgr = DatabaseManager(use_sqlite=True)
        else:
            dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
            db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)
        initialize_database_if_empty(db_mgr)
    else:
        db_mgr = db_manager

    controller = OrchestratorController(
        db_manager=db_mgr,
        openapi_client=openapi_client,
        rabbitmq_client=rabbitmq_client
    )
    process_number = task_payload.get("num_processo", 0)

    try:
        logger.info(f"Processando tarefa #{process_number}...")
        result = controller.execute_workflow(task_payload)
        logger.info(f"Tarefa #{process_number} finalizada com SUCESSO!")
        return result
    except BaseFlowException as err:
        logger.error(f"--> [ERRO DE FLUXO MAPEADO: {err.flow_error_code}] <--")
        logger.error(f"Mensagem: {err.message}")
        parecer_html = err.to_fluid_parecer()

        return {
            "status": "ERRO_FLUXO",
            "codigo_erro": err.flow_error_code,
            "detalhes_erros": err.errors,
            "parecer_fluid": parecer_html
        }
    except Exception as err:
        logger.exception(f"--> [ERRO INESPERADO] {err}")
        return {
            "status": "ERRO_INESPERADO",
            "codigo_erro": "UNEXPECTED_ERROR",
            "detalhes_erros": [str(err)],
            "parecer_fluid": f"Erro inesperado no robô: {str(err)}"
        }
