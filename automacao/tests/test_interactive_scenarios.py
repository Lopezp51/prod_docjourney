"""
Suíte Interativa de 6 Cenários de Testes da Automação e Microsserviço DocJourney.
Demonstra passo a passo:
1. Criação de envelope inicial por cluster documental (Versão 1).
2. Substituição seletiva por alteração de documento (Versão 2).
3. Substituição seletiva por inclusão de signatário (Versão 3).
4. Motor de pré-validação eager ('tudo de uma vez').
5. Rotina de expiração (> 60 dias) com auditoria de manutenção.
6. Disparo de notificação de status ao gestor.
Nomes de métodos e variáveis em inglês com docstrings em português.
"""

import os
import sys
from datetime import datetime, timedelta
from uuid import uuid4

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Suporte a UTF-8 no Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.infrastructure.repositories import (
    JourneyRepository,
    EnvelopeRepository,
    MaintenanceHistoryRepository
)
from microservico.domain.enums import EnvelopeStatus, MaintenanceReason, ProviderType, AutomationNode
from automacao.main import run_automation_task
from automacao.controllers.orchestrator_ctr import OrchestratorController
from automacao.infrastructure.openapi_client import OpenApiV2Client
from microservico.notifier.client import ExternalStatusNotifierClient, StatusNotificationPayload, SignerStatusNotificationPayload
from microservico.config import config


def print_header(title: str):
    """Exibe cabeçalho formatado no console."""
    print("\n" + "=" * 80)
    print(f"📌 {title}")
    print("=" * 80)


def run_all_scenarios(use_sqlite: bool = False):
    """
    Executa os 6 cenários de teste da esteira, exibindo logs detalhados e alterações no banco de dados.

    Parâmetros:
        use_sqlite (bool): Se True, executa no SQLite em memória. Se False, conecta ao PostgreSQL real.
    """
    print_header("INICIANDO SUÍTE COMPLETA DE TESTES INTERATIVOS DO ORQUESTRADOR")

    if not use_sqlite:
        dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
        print(f"📡 Conectando ao PostgreSQL em: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME} (Usuário: {config.DB_USER})...")
        db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)
    else:
        print("📡 Executando em modo SQLite isolado em memória...")
        db_mgr = DatabaseManager(use_sqlite=True)

    initialize_database_if_empty(db_mgr)
    openapi_client = OpenApiV2Client(mock_mode=True if use_sqlite else False)
    controller = OrchestratorController(db_manager=db_mgr, openapi_client=openapi_client)
    env_repo = EnvelopeRepository(db_mgr)
    journey_repo = JourneyRepository(db_mgr)
    manut_repo = MaintenanceHistoryRepository(db_mgr)

    # -------------------------------------------------------------------------
    # CENÁRIO 1: Criação Inicial de Envelope (Versão 1)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 1: Criação Inicial de Envelopes por Cluster Documental (Versão 1)")
    payload_c1 = {
        "_id": {"$oid": "scen1_mongo_id_001"},
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
                {"nome": "765 - CCB", "hash": "hash_ccb_v1", "tipo_doc_id": 765, "extensao": "pdf"}
            ]
        }
    }

    res_c1 = controller.execute_workflow(payload_c1)
    journey_c1 = journey_repo.get_by_mongo_id("scen1_mongo_id_001")
    env_c1 = env_repo.get_by_id(res_c1["envelopes"][0]["envelope_db_id"])

    print(f"✅ Processo #{res_c1['process_number']} Criado com SUCESSO!")
    print(f"   -> Jornada ID: {journey_c1.id}")
    print(f"   -> Envelope ID no Banco: {env_c1.id}")
    print(f"   -> ID Externo (OpenAPI): {env_c1.external_envelope_id}")
    print(f"   -> Versão do Envelope: {env_c1.envelope_version}")
    print(f"   -> Status do Envelope: {env_c1.envelope_status}")
    print(f"   -> Hash do Escopo Documental: {env_c1.document_scope_hash[:16]}...")

    # -------------------------------------------------------------------------
    # CENÁRIO 2: Alteração de Versão de Documento (Substituição Seletiva)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 2: Alteração de Versão do Documento (Substituição Seletiva)")
    print("ℹ️ Reenviando a mesma tarefa #200001 com novo hash do arquivo '765 - CCB'...")

    payload_c2 = {
        "_id": {"$oid": "scen1_mongo_id_001"},  # Mesmo mongo_id
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "026.313.539-00"},
                        {"id": 12910, "valor": "Edilson Paulo de Franca"},
                        {"id": 12911, "valor": "Titular"},
                        {"id": 12857, "valor": '["765 - CCB V2 Nova"]'},  # Documento alterado
                        {"id": 12912, "valor": "E-mail"},
                        {"id": 12913, "valor": "edilson@sicredi.com.br"},
                        {"id": 12915, "valor": "Eletrônica"}
                    ]
                ]
            },
            "anexos": [
                {"nome": "765 - CCB V2 Nova", "hash": "hash_ccb_v2_novo", "tipo_doc_id": 765, "extensao": "pdf"}
            ]
        }
    }

    res_c2 = controller.execute_workflow(payload_c2)
    old_env_c1 = env_repo.get_by_id(env_c1.id)
    new_env_c2 = env_repo.get_by_id(res_c2["envelopes"][0]["envelope_db_id"])

    print("🔄 RESULTADO DA SUBSTITUIÇÃO SELETIVA:")
    print(f"   1. Envelope Antigo (Versão 1 - ID: {old_env_c1.id}):")
    print(f"      - Status Atualizado para: {old_env_c1.envelope_status} (Esperado: REPLACED_CANCELED)")
    print(f"   2. Novo Envelope Criado (Versão 2 - ID: {new_env_c2.id}):")
    print(f"      - Status: {new_env_c2.envelope_status} (Esperado: PENDING_SIGNATURE)")
    print(f"      - Versão Incremental: {new_env_c2.envelope_version} (Esperado: 2)")

    # -------------------------------------------------------------------------
    # CENÁRIO 3: Inclusão / Alteração de Signatário no Envelope
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 3: Inclusão de Novo Signatário (Cônjuge Avalista)")
    print("ℹ️ Reenviando a mesma tarefa adicionando a esposa 'Aila Franca' no envelope...")

    payload_c3 = {
        "_id": {"$oid": "scen1_mongo_id_001"},
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
                    ],
                    [
                        {"id": 12909, "valor": "111.580.729-37"},  # Novo Signatário
                        {"id": 12910, "valor": "Aila Elo de Franca"},
                        {"id": 12911, "valor": "Cônjuge Avalista"},
                        {"id": 12857, "valor": '["765 - CCB V2 Nova"]'},
                        {"id": 12912, "valor": "WhatsApp Enterprise"},
                        {"id": 12914, "valor": "(42) 99984-3189"},
                        {"id": 12915, "valor": "Eletrônica"}
                    ]
                ]
            },
            "anexos": [
                {"nome": "765 - CCB V2 Nova", "hash": "hash_ccb_v2_novo", "tipo_doc_id": 765, "extensao": "pdf"}
            ]
        }
    }

    res_c3 = controller.execute_workflow(payload_c3)
    old_env_c2 = env_repo.get_by_id(new_env_c2.id)
    new_env_c3 = env_repo.get_by_id(res_c3["envelopes"][0]["envelope_db_id"])

    print("🔄 RESULTADO DA ADIÇÃO DE SIGNATÁRIO:")
    print(f"   1. Envelope Versão 2 (ID: {old_env_c2.id}):")
    print(f"      - Status Atualizado para: {old_env_c2.envelope_status} (Esperado: REPLACED_CANCELED)")
    print(f"   2. Novo Envelope Criado (Versão 3 - ID: {new_env_c3.id}):")
    print(f"      - Signatários no Cluster: {res_c3['envelopes'][0]['signers_count']} (Edilson + Aila)")
    print(f"      - Versão Incremental: {new_env_c3.envelope_version} (Esperado: 3)")

    # -------------------------------------------------------------------------
    # CENÁRIO 4: Engine de Pré-Validação Completa ("Tudo de uma Vez")
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 4: Teste de Pré-Validação Aggregada (Acúmulo de Múltiplos Erros)")
    print("ℹ️ Enviando payload com CPF inválido + E-mail inválido + Anexo Faltante...")

    payload_c4_invalid = {
        "_id": {"$oid": "scen4_mongo_id_invalido"},
        "num_processo": 999004,
        "nome_processo": "Processo Teste Erros",
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "111.111.111-11"},  # CPF com erro
                        {"id": 12910, "valor": "João Silva Erros"},
                        {"id": 12857, "valor": '["Documento Inexistente.pdf"]'},  # Anexo Faltante
                        {"id": 12912, "valor": "E-mail"},
                        {"id": 12913, "valor": "email_sem_arroba_errado"}  # E-mail com erro
                    ]
                ]
            },
            "anexos": []
        }
    }

    res_c4 = run_automation_task(payload_c4_invalid, use_sqlite=use_sqlite, db_manager=db_mgr)

    print("⚠️ RESULTADO DA PRÉ-VALIDAÇÃO COMPLETA:")
    print(f"   -> Status Retornado: {res_c4['status']} (Esperado: ERRO_FLUXO)")
    print(f"   -> Código de Erro: {res_c4['codigo_erro']} (Esperado: VAL_BULK_ERROR)")
    print(f"   -> Múltiplas Pendências Capturadas de Uma Vez ({len(res_c4['detalhes_erros'])} erros):")
    for idx, err_msg in enumerate(res_c4['detalhes_erros'], 1):
        print(f"      {idx}. {err_msg}")
    print("\n   -> Trecho do Parecer HTML retornado para o Fluid:")
    print(f"      {res_c4['parecer_fluid'][:200]}...")

    # -------------------------------------------------------------------------
    # CENÁRIO 5: Rotina de Expiração de Envelopes (> 60 Dias) e Auditoria
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 5: Rotina de Expiração por 60 Dias e Auditoria de Manutenção")

    # Simula um envelope antigo criado no banco com data de expiração no passado
    exp_suffix = uuid4().hex[:8]
    journey_exp = journey_repo.create_journey(
        process_id=journey_c1.process_id,
        mongo_id=f"scen5_expirado_{exp_suffix}",
        process_number=500005,
        fluid_payload={}
    )
    env_exp = env_repo.create_envelope(
        request_id=journey_exp.id,
        document_scope_hash=f"hash_expirado_{exp_suffix}",
        provider=ProviderType.CERTISIGN
    )
    env_repo.update_external_id(env_exp.id, f"openapi_env_exp_{exp_suffix}", EnvelopeStatus.PENDING_SIGNATURE)

    # Atualiza a data no SQL direto para simular 61 dias no passado
    conn = db_mgr.get_connection()
    past_date = (datetime.now() - timedelta(days=61)).isoformat() if db_mgr.use_sqlite else (datetime.now() - timedelta(days=61))
    sql_exp = "UPDATE envelopes SET expired_at = %s WHERE id = %s" if not db_mgr.use_sqlite else "UPDATE envelopes SET expired_at = ? WHERE id = ?"
    params_exp = (past_date, str(env_exp.id))
    if db_mgr.use_sqlite:
        conn.execute(sql_exp, params_exp)
        conn.commit()
    else:
        with conn.cursor() as cur:
            cur.execute(sql_exp, params_exp)
        conn.commit()
        conn.close()

    # Executa a busca de expirados > 60 dias
    expired_list = env_repo.list_expired_over_60_days()
    print(f"🔍 Envelopes identificados com mais de 60 dias pendentes: {len(expired_list)}")
    for env in expired_list:
        print(f"   -> Envelope ID: {env.id} | External ID: {env.external_envelope_id}")
        # Loga auditoria de manutenção
        log_m = manut_repo.log_maintenance(
            request_id=env.request_id,
            envelope_id=env.id,
            reason_code=MaintenanceReason.EXPIRED_60_DAYS,
            detailed_description=f"Envelope {env.external_envelope_id} expirou após 60 dias pendente."
        )
        print(f"   ✅ Auditoria Registrada no Banco! ID Log: {log_m.id} | Motivo: {log_m.reason_code}")

    # -------------------------------------------------------------------------
    # CENÁRIO 6: Notificador de Status ao Gestor (ExternalStatusNotifierClient)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 6: Disparo de Notificação de Status ao Gestor / Outro Microserviço")
    notifier_client = ExternalStatusNotifierClient()
    payload_notif = StatusNotificationPayload(
        process_number=200001,
        envelope_id=new_env_c3.external_envelope_id or "openapi_env_v3",
        envelope_status="COMPLETED",
        updated_at=datetime.now().isoformat(),
        signers=[
            SignerStatusNotificationPayload(tax_id="02631353900", name="Edilson Paulo de Franca", signature_status="SIGNED"),
            SignerStatusNotificationPayload(tax_id="11158072937", name="Aila Elo de Franca", signature_status="SIGNED")
        ]
    )

    sent_success = notifier_client.notify_status_change(payload_notif)
    print("🔔 DISPARO DE WEBHOOK PARA O GESTOR:")
    print(f"   -> Payload Enviado: Processo #{payload_notif.process_number} | Envelope: {payload_notif.envelope_id}")
    print(f"   -> Signatários Notificados: {len(payload_notif.signers)}")
    print(f"   -> Status da Chamada Webhook: {'SUCESSO (200 OK)' if sent_success else 'FALHA'}")

    # -------------------------------------------------------------------------
    # CENÁRIO 7: Detecção de Documento Corrompido / Vazio (Instabilidade AWS/Fluid)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 7: Detecção de Documento Corrompido / Vazio (Falha AWS / Fluid)")
    corrupted_mongo_id = f"mongo_corrupted_{uuid4().hex[:8]}"
    payload_corrupted = {
        "_id": {"$oid": corrupted_mongo_id},
        "num_processo": 778899,
        "nome_processo": "Financiamento Agro - Documento Ilegível",
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "111.580.729-37"},
                        {"id": 12910, "valor": "Mariana Valida"},
                        {"id": 12857, "valor": '["765 - CCB", "613 - Seguro"]'},
                        {"id": 12912, "valor": "E-mail"},
                        {"id": 12913, "valor": "mariana@sicredi.com.br"}
                    ]
                ]
            },
            "anexos": [
                # Documento 1: Corrompido por ter 0 bytes (arquivo vazio gerado por instabilidade AWS)
                {
                    "nome": "765 - CCB.pdf",
                    "hash": "hash_aws_corrupted_1",
                    "tipo_doc_id": 765,
                    "tamanho": 0,
                    "extensao": "pdf"
                },
                # Documento 2: Vaga criada no Fluid mas sem nenhum arquivo atribuído (hash vazio)
                {
                    "nome": "613 - Seguro.pdf",
                    "hash": "",
                    "tipo_doc_id": 613,
                    "extensao": "pdf"
                }
            ]
        }
    }

    result_corrupted = run_automation_task(payload_corrupted, use_sqlite=db_mgr.use_sqlite, db_manager=db_mgr)
    print("🚨 RESULTADO DA VALIDAÇÃO DE ARQUIVOS QUEBRADOS:")
    print(f"   -> Status Retornado: {result_corrupted['status']} (Esperado: ERRO_FLUXO)")
    print(f"   -> Código de Erro: {result_corrupted['codigo_erro']} (Esperado: CORRUPTED_DOCUMENT_ERROR)")
    print(f"   -> Detalhes das Falhas Detectadas ({len(result_corrupted['detalhes_erros'])} arquivos):")
    for d_err in result_corrupted["detalhes_erros"]:
        print(f"      ❌ {d_err}")

    print("\n   -> Trecho do Parecer HTML retornado para a esteira Fluid:")
    print("      " + result_corrupted["parecer_fluid"][:180] + "...")

    # -------------------------------------------------------------------------
    # CENÁRIO 8: Troca de Método de Assinatura via Nodo 13 (E-mail -> WhatsApp)
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 8: Troca de Método de Assinatura via Nodo 13 (E-mail -> WhatsApp)")
    print("ℹ️ Enviando payload com nodo=13 para alterar canal de 'Edilson' para WhatsApp...")

    payload_c8_nodo13 = {
        "_id": {"$oid": "scen1_mongo_id_001"},
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "nodo": AutomationNode.UPDATE_SIGNATURE_METHOD.value,  # Nodo 13
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "026.313.539-00"},
                        {"id": 12910, "valor": "Edilson Paulo de Franca"},
                        {"id": 12911, "valor": "Titular"},
                        {"id": 12857, "valor": '["765 - CCB V2 Nova"]'},
                        {"id": 12912, "valor": "WhatsApp"},  # Novo canal
                        {"id": 12914, "valor": "(42) 99984-3189"},  # Telefone para autenticação WhatsApp
                        {"id": 12915, "valor": "Eletrônica"}
                    ]
                ]
            },
            "anexos": [
                {"nome": "765 - CCB V2 Nova", "hash": "hash_ccb_v2_novo", "tipo_doc_id": 765, "extensao": "pdf"}
            ]
        }
    }

    # Executa a troca de canal
    res_c8 = controller.execute_workflow(payload_c8_nodo13)

    old_env_c8 = env_repo.get_by_id(res_c8["old_envelope_id"])
    new_env_c8 = env_repo.get_by_id(res_c8["new_envelope_id"])

    print("🔄 RESULTADO DA TROCA DE MÉTODO DE ASSINATURA (NODO 13):")
    print(f"   -> Ação Executada: {res_c8['action']} (Nodo {res_c8['nodo']})")
    print(f"   1. Envelope Anterior (ID: {old_env_c8.id}):")
    print(f"      - is_altered: {old_env_c8.is_altered} (Esperado: True)")
    print(f"      - Status: {old_env_c8.envelope_status} (Esperado: ALTERADO)")
    print(f"      - Substituído por ID Externo: {old_env_c8.replaced_by_external_id}")
    print(f"   2. Novo Envelope Versionado (ID: {new_env_c8.id}):")
    print(f"      - Versão Incremental: {new_env_c8.envelope_version} (Esperado: {old_env_c8.envelope_version + 1})")
    print(f"      - Novo ID Externo: {new_env_c8.external_envelope_id}")
    print(f"      - is_altered: {new_env_c8.is_altered} (Esperado: False)")
    print(f"      - Status: {new_env_c8.envelope_status} (Esperado: PENDING_SIGNATURE)")

    assert old_env_c8.is_altered is True
    assert old_env_c8.envelope_status == EnvelopeStatus.ALTERADO
    assert old_env_c8.replaced_by_external_id == new_env_c8.external_envelope_id
    assert new_env_c8.is_altered is False

    # -------------------------------------------------------------------------
    # CENÁRIO 9: Resiliência contra o erro transitório 'Aguardando envio'
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 9: Resiliência Automática contra Status 'Aguardando Envio' (Retry Backoff)")
    print("ℹ️ Configurando cliente OpenAPI para simular 2 rejeições 'Aguardando envio' seguidas de sucesso...")

    # Cria cliente OpenAPI com 2 falhas transitórias simuladas
    openapi_resilient = OpenApiV2Client(mock_mode=True, mock_transient_retries=2)
    controller_resilient = OrchestratorController(db_manager=db_mgr, openapi_client=openapi_resilient)

    payload_c9_retry = {
        "_id": {"$oid": "scen1_mongo_id_001"},
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "nodo": 13,
        "infos_envio": {
            "atributos": {
                "12905": [
                    [
                        {"id": 12909, "valor": "026.313.539-00"},
                        {"id": 12910, "valor": "Edilson Paulo de Franca"},
                        {"id": 12911, "valor": "Titular"},
                        {"id": 12857, "valor": '["765 - CCB V2 Nova"]'},
                        {"id": 12912, "valor": "E-mail"},  # Volta para E-mail
                        {"id": 12913, "valor": "edilson.franca@sicredi.com.br"},
                        {"id": 12915, "valor": "Eletrônica"}
                    ]
                ]
            }
        }
    }

    res_c9 = controller_resilient.execute_workflow(payload_c9_retry)
    print("✅ RETENTATIVA BEM-SUCEDIDA APÓS ESTADO 'AGUARDANDO ENVIO':")
    print(f"   -> Status da Operação: {res_c9['status']}")
    print(f"   -> Retentativas Simuladas: {openapi_resilient._current_retry_count} (Esperado: 2)")
    print(f"   -> Novo Envelope ID Externo: {res_c9['new_external_id']}")
    assert openapi_resilient._current_retry_count == 2
    assert res_c9["status"] == "SUCESSO"

    # -------------------------------------------------------------------------
    # CENÁRIO 10: Cancelamento Explícito de Envelope via Nodo 16
    # -------------------------------------------------------------------------
    print_header("CENÁRIO 10: Cancelamento Explícito de Envelope Ativo (Nodo 16)")
    print("ℹ️ Enviando tarefa com nodo=16 para cancelar envelope ativo da solicitação #200001...")

    payload_c10_cancel = {
        "_id": {"$oid": "scen1_mongo_id_001"},
        "num_processo": 200001,
        "nome_processo": "Solicitação de Crédito Comercial V2",
        "nodo": AutomationNode.CANCEL_ENVELOPE.value,  # Nodo 16
        "motivo_cancelamento": "Associado desistiu da operação antes da assinatura"
    }

    res_c10 = controller.execute_workflow(payload_c10_cancel)
    canceled_env = env_repo.get_by_id(res_c10["envelope_id"])

    print("🛑 RESULTADO DO CANCELAMENTO (NODO 16):")
    print(f"   -> Ação: {res_c10['action']} (Nodo {res_c10['nodo']})")
    print(f"   -> Envelope ID Cancelado: {canceled_env.id}")
    print(f"   -> Status no Banco: {canceled_env.envelope_status} (Esperado: CANCELED)")
    print(f"   -> Motivo Registrado: {res_c10['reason']}")
    assert canceled_env.envelope_status == EnvelopeStatus.CANCELED

    print("\n" + "=" * 80)
    print("🎉 SUÍTE COMPLETA DE 10 CENÁRIOS INTERATIVOS FINALIZADA COM 100% DE SUCESSO!")
    print("=" * 80)
    return True


if __name__ == "__main__":
    use_sqlite_flag = "--sqlite" in sys.argv
    run_all_scenarios(use_sqlite=use_sqlite_flag)

