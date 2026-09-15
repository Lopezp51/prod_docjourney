"""
Ponto de Entrada Principal da Automação RPA (DocJourney Automation).
Executa o processamento de tarefas vindas do MongoDB/Fluid e gera retornos formatados para a esteira.
Comunicação desacoplada exclusivamente com a API REST do Microsserviço via MicroserviceApiClient.
Nomes de funções, parâmetros e variáveis 100% em inglês com docstrings explicativas em português.
"""

import logging
from typing import Dict, Any, Optional

from automacao.domain.exceptions import BaseFlowException
from automacao.controllers.orchestrator_ctr import OrchestratorController
from automacao.infrastructure.microservice_client import MicroserviceApiClient
from automacao.infrastructure.openapi_client import OpenApiV2Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("RPA_Automation")


def run_automation_task(
    task_payload: Dict[str, Any],
    api_client: Optional[MicroserviceApiClient] = None,
    openapi_client: Optional[OpenApiV2Client] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Função principal de processamento de uma tarefa recebida da esteira Fluid / MongoDB.

    Captura de forma unificada as exceções do tipo BaseFlowException e gera o parecer
    formatado em HTML para devolução imediata à esteira em caso de pendências.
    Não executa conexões locais nem manipula o banco de dados diretamente; toda
    a governança e persistência é delegada à API REST do Microsserviço.

    Parâmetros:
        task_payload (Dict[str, Any]): Metadados e documentos da tarefa do processo.
        api_client (Optional[MicroserviceApiClient]): Cliente REST com o microsserviço (ou mock para testes).
        openapi_client (Optional[OpenApiV2Client]): Instância customizada do cliente OpenAPI v2 (opcional).

    Retorno:
        Dict[str, Any]: Dicionário com resultado da execução ('SUCESSO', 'ERRO_FLUXO' ou 'ERRO_INESPERADO').
    """
    client = api_client or MicroserviceApiClient()
    controller = OrchestratorController(
        api_client=client,
        openapi_client=openapi_client
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
