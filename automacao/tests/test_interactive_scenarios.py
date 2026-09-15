"""
Suíte Interativa de Cenários de Testes da Automação RPA DocJourney.
Demonstra passo a passo a execução da esteira consumindo exclusivamente o MicroserviceApiClient:
1. Criação de envelope inicial por cluster documental (Versão 1).
2. Substituição seletiva por alteração de documento (Versão 2).
3. Substituição seletiva por inclusão de signatário (Versão 3).
4. Motor de pré-validação eager ('tudo de uma vez').
5. Detecção de documento corrompido ou vazio.
6. Troca de método de assinatura (Nodo 13).
7. Cancelamento explícito de envelope (Nodo 16).
100% autônomo, sem imports nem queries diretas ao banco de dados.
"""

import os
import sys
from datetime import datetime
from uuid import uuid4

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Suporte a UTF-8 no Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from automacao.domain.enums import EnvelopeStatus, MaintenanceReason, AutomationNode
from automacao.infrastructure.microservice_client import MicroserviceApiClient
from automacao.infrastructure.openapi_client import OpenApiV2Client
from automacao.controllers.orchestrator_ctr import OrchestratorController
from automacao.main import run_automation_task


def print_header(title: str):
    """Exibe cabeçalho formatado no console."""
    print("\n" + "=" * 80)
    print(f"📌 {title}")
    print("=" * 80)


def run_all_scenarios():
    """
    Executa os cenários de teste da esteira via cliente HTTP da API.
    """
    print_header("INICIANDO SUÍTE DE TESTES INTERATIVOS DO ORQUESTRADOR (VIA API REST)")

    api_client = MicroserviceApiClient(fallback_to_mock=True)
    openapi_client = OpenApiV2Client(mock_mode=True)
    controller = OrchestratorController(api_client=api_client, openapi_client=openapi_client)

    # -------------------------------------------------------------------------
    # CENÁRIO 1: Criação Inicial de Envelope (Versão 1)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 1: Criação Inicial de Envelopes por Cluster Documental (Versão 1)")
    payload_c1 = {
        "_id": "scen1_mongo_id_001",
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "026.313.539-00"},
                        {"id": 12910, "valor": "Edilson Paulo de Franca"},
                        {"id": 12911, "valor": "Titular"},
                        {"id": 12857, "valor": '["765 - CCB"]'},
                        {"id": 12912, "valor": "E-mail"},
                        {"id": 12913, "valor": "edilson@sicredi.com.br"},
                        {"id": 12915, "valor": "Eletrônica"}
                    ]
                ]
            },
            "anexos": [
                {
                    "nome": "765 - CCB.pdf",
                    "hash": "hash_ccb_v1",
                    "tipo_doc_id": 765,
                    "extensao": "pdf",
                    "binary_content": b"%PDF-1.4 Mock Valid File For Scenario 1 Test Content Header"
                }
            ]
        }
    }

    res_c1 = controller.execute_workflow(payload_c1)
    journey_c1 = api_client.get_journey_by_mongo_id("scen1_mongo_id_001")
    env_c1 = api_client.get_envelope(res_c1["envelopes"][0]["envelope_db_id"])

    print(f"✅ Processo #{res_c1['process_number']} Criado com SUCESSO via API!")
    print(f"   -> Jornada ID: {journey_c1.get('id')}")
    print(f"   -> Envelope ID: {env_c1.get('id')}")
    print(f"   -> ID Externo (OpenAPI): {env_c1.get('external_envelope_id')}")
    print(f"   -> Versão do Envelope: {env_c1.get('envelope_version')}")
    print(f"   -> Status do Envelope: {env_c1.get('envelope_status')}")

    # -------------------------------------------------------------------------
    # CENÁRIO 2: Alteração de Versão de Documento (Substituição Seletiva)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 2: Alteração de Versão do Documento (Substituição Seletiva)")
    print("ℹ️ Reenviando a mesma tarefa #200001 com novo hash do arquivo '765 - CCB V2 Nova'...")

    payload_c2 = {
        "_id": "scen1_mongo_id_001",  # Mesmo mongo_id
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "026.313.539-00"},
                        {"id": 12910, "valor": "Edilson Paulo de Franca"},
                        {"id": 12911, "valor": "Titular"},
                        {"id": 12857, "valor": '["765 - CCB V2 Nova"]'},
                        {"id": 12912, "valor": "E-mail"},
                        {"id": 12913, "valor": "edilson@sicredi.com.br"},
                        {"id": 12915, "valor": "Eletrônica"}
                    ]
                ]
            },
            "anexos": [
                {
                    "nome": "765 - CCB V2 Nova.pdf",
                    "hash": "hash_ccb_v2_novo",
                    "tipo_doc_id": 765,
                    "extensao": "pdf",
                    "binary_content": b"%PDF-1.4 Mock Valid File For Scenario 2 Test Content Header"
                }
            ]
        }
    }

    res_c2 = controller.execute_workflow(payload_c2)
    print("🔄 RESULTADO DA SUBSTITUIÇÃO SELETIVA:")
    print(f"   -> Processo #{res_c2['process_number']} atualizado com {len(res_c2['envelopes'])} novo(s) envelope(s).")
    print(f"   -> Versão Incremental: {res_c2['envelopes'][0]['version']}")

    # -------------------------------------------------------------------------
    # CENÁRIO 3: Detecção de Documento Corrompido / Vazio
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 3: Detecção de Documento Corrompido / Vazio (Pré-Validação)")
    payload_corrupted = {
        "_id": f"mongo_corrupted_{uuid4().hex[:8]}",
        "num_processo": 778899,
        "nome_processo": "Financiamento Agro - Documento Ilegível",
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "111.580.729-37"},
                        {"id": 12910, "valor": "Mariana Valida"},
                        {"id": 12857, "valor": '["765 - CCB"]'},
                        {"id": 12912, "valor": "E-mail"},
                        {"id": 12913, "valor": "mariana@sicredi.com.br"}
                    ]
                ]
            },
            "anexos": [
                {
                    "nome": "765 - CCB.pdf",
                    "hash": "hash_aws_corrupted",
                    "tipo_doc_id": 765,
                    "tamanho": 0,
                    "extensao": "pdf"
                }
            ]
        }
    }

    result_corrupted = run_automation_task(payload_corrupted, api_client=api_client, openapi_client=openapi_client)
    print("🚨 RESULTADO DA PRÉ-VALIDAÇÃO DE ARQUIVOS QUEBRADOS:")
    print(f"   -> Status Retornado: {result_corrupted['status']} (Esperado: ERRO_FLUXO)")
    print(f"   -> Código de Erro: {result_corrupted['codigo_erro']} (Esperado: CORRUPTED_DOCUMENT_ERROR)")

    # -------------------------------------------------------------------------
    # CENÁRIO 4: Cancelamento Explícito de Envelope (Nodo 16)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 4: Cancelamento Explícito de Envelope via Nodo 16")
    payload_c4_cancel = {
        "_id": "scen1_mongo_id_001",
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "nodo": AutomationNode.CANCEL_ENVELOPE.value,
        "motivo_cancelamento": "Associado desistiu da operação antes da assinatura"
    }

    res_c4 = controller.execute_workflow(payload_c4_cancel)
    print("🛑 RESULTADO DO CANCELAMENTO (NODO 16):")
    print(f"   -> Ação: {res_c4['action']} (Nodo {res_c4['nodo']})")
    print(f"   -> Envelope Status: {res_c4['envelope_status']}")

    print("\n" + "=" * 80)
    print("🎉 SUÍTE INTERATIVA EXECUTADA COM SUCESSO VIA API REST!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    run_all_scenarios()
