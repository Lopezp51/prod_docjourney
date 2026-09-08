"""
Teste de Integração End-to-End (E2E) com Banco PostgreSQL Real.
Valida o schema PROD_schema.sql, carga de dados e fluxo do RPA persistido diretamente no PostgreSQL.
Nomes 100% em inglês com docstrings em português.
"""

import os
import sys

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Suporte a UTF-8 no Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.infrastructure.repositories import (
    AssociateRepository,
    JourneyRepository,
    EnvelopeRepository
)
from microservico.config import config


def run_postgres_e2e_test():
    """
    Executa o teste E2E conectando diretamente à base de dados PostgreSQL real.
    Verifica a criação das tabelas em inglês, a execução do fluxo da automação e a integridade relacional.
    """
    print("=" * 70)
    print("INICIANDO TESTE E2E COM BANCO POSTGRESQL REAL")
    print("=" * 70)

    dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
    print(f"Conectando ao PostgreSQL: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME} (Usuário: {config.DB_USER})...")

    db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)

    try:
        # 1. Inicializa o PROD_schema.sql e seed data no Postgres
        print("1. Criando tabelas e inserindo dados de seed no PostgreSQL se estiver vazio...")
        initialize_database_if_empty(db_mgr)
        print("   -> Tabelas e índices verificados/criados com sucesso!")

        # 2. Executa a automação RPA com um Payload de teste no Postgres
        print("\n2. Executando tarefa de teste da Automação RPA no PostgreSQL...")
        mongo_payload = {
            "_id": {"$oid": "6a9b225987db9287e3dde60c"},
            "num_processo": 1225591,
            "nome_processo": "Solicitação de Crédito Comercial V2",
            "infos_envio": {
                "atributos": {
                    "3305": "EDILSON PAULO DE FRANCA",
                    "4335": "02631353900",
                    "11675": "francaedilson78@gmail.com",
                    "12044": "(42) 98818-7402",
                    "12905": [
                        [
                            {"id": 12906, "valor": "1"},
                            {"id": 12909, "valor": "111.580.729-37"},
                            {"id": 12910, "valor": "EDILSON PAULO DE FRANCA"},
                            {"id": 12911, "valor": "Titular"},
                            {"id": 12857, "valor": '["765 - CCB", "678 - CET"]'},
                            {"id": 12912, "valor": "E-mail"},
                            {"id": 12913, "valor": "pedro_hlopes@sicredi.com.br"},
                            {"id": 12915, "valor": "Eletrônica"}
                        ]
                    ]
                },
                "anexos": [
                    {"nome": "765 - CCB", "hash": "hash_ccb_123", "tipo_doc_id": 765, "extensao": "pdf"},
                    {"nome": "678 - CET", "hash": "hash_cet_123", "tipo_doc_id": 678, "extensao": "pdf"}
                ]
            }
        }

        from automacao.controllers.orchestrator_ctr import OrchestratorController
        controller = OrchestratorController(db_manager=db_mgr)
        result = controller.execute_workflow(mongo_payload)

        print("   -> Resultado do Fluxo RPA:")
        print(f"      - Status: {result['status']}")
        print(f"      - Processo: #{result['process_number']}")
        print(f"      - Clusters Criados: {result['clusters_count']}")
        print(f"      - Envelopes: {result['envelopes']}")

        # 3. Consulta e validação direta nos repositórios PostgreSQL
        print("\n3. Validando registros gravados no banco PostgreSQL...")
        journey_repo = JourneyRepository(db_mgr)
        journey_db = journey_repo.get_by_mongo_id("6a9b225987db9287e3dde60c")
        print(f"   -> Jornada ID no Postgres: {journey_db.id} (Status: {journey_db.status})")

        env_repo = EnvelopeRepository(db_mgr)
        scope_hash = result['envelopes'][0]['scope_hash']
        envelope_db = env_repo.get_active_by_request_and_hash(journey_db.id, scope_hash)
        print(f"   -> Envelope ID no Postgres: {envelope_db.id} (Hash: {envelope_db.document_scope_hash[:16]}...)")

        assoc_repo = AssociateRepository(db_mgr)
        assoc_db = assoc_repo.get_by_tax_id("111.580.729-37")
        if assoc_db:
            print(f"   -> Associado Gravado: {assoc_db.name} (Tax ID: {assoc_db.tax_id})")

        print("\n" + "=" * 70)
        print("TESTE E2E COM POSTGRESQL REAL FINALIZADO COM SUCESSO ABSOLUTO!")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"\n[ERRO NO TESTE E2E POSTGRESQL]: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_postgres_e2e_test()
    sys.exit(0 if success else 1)
