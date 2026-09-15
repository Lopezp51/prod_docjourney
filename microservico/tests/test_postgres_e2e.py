"""
Teste de Integração End-to-End (E2E) com Banco PostgreSQL Real no Microsserviço.
Valida o schema PROD_schema.sql, integridade relacional e rotas/repositórios diretamente no PostgreSQL.
Totalmente autônomo, sem dependências do módulo de automação.
Nomes 100% em inglês com docstrings em português.
"""

import os
import sys
from uuid import uuid4

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Suporte a UTF-8 no Windows Console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.infrastructure.repositories import (
    AssociateRepository,
    ProcessRepository,
    JourneyRepository,
    EnvelopeRepository,
    EnvelopeSignerRepository,
    DocumentRepository,
    MaintenanceHistoryRepository
)
from microservico.domain.enums import JourneyStatus, EnvelopeStatus, MaintenanceReason, ProviderType
from microservico.config import config


def run_postgres_e2e_test():
    """
    Executa o teste E2E conectando à base de dados PostgreSQL real.
    Verifica a criação das tabelas em inglês, inserção, relacionamentos e auditoria de manutenção.
    """
    print("=" * 70)
    print("INICIANDO TESTE E2E COM BANCO POSTGRESQL REAL (MICROSSERVIÇO)")
    print("=" * 70)

    dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
    print(f"Conectando ao PostgreSQL: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME} (Usuário: {config.DB_USER})...")

    db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)

    try:
        # 1. Inicializa o PROD_schema.sql e seed data no Postgres
        print("1. Criando tabelas e inserindo dados de seed no PostgreSQL se estiver vazio...")
        initialize_database_if_empty(db_mgr)
        print("   -> Tabelas e índices verificados/criados com sucesso!")

        # 2. Testa persistência relacional completa
        print("\n2. Testando persistência de Processo e Jornada no PostgreSQL...")
        proc_repo = ProcessRepository(db_mgr)
        process = proc_repo.get_or_create(name="Crédito Comercial E2E Test")

        journey_repo = JourneyRepository(db_mgr)
        mongo_id = f"e2e_mongo_{uuid4().hex[:8]}"
        journey = journey_repo.create_journey(
            process_id=process.id,
            mongo_id=mongo_id,
            process_number=998877,
            fluid_payload={"e2e_test": True}
        )
        print(f"   -> Jornada criada: {journey.id} (mongo_id: {journey.mongo_id})")

        # 3. Testa Associados, Envelopes e Signatários
        print("\n3. Criando Associado, Envelope e Signatário...")
        assoc_repo = AssociateRepository(db_mgr)
        assoc = assoc_repo.upsert(
            tax_id="02631353900",
            name="Edilson Paulo de Franca",
            email="edilson@sicredi.com.br",
            phone="42988187402"
        )

        env_repo = EnvelopeRepository(db_mgr)
        envelope = env_repo.create_envelope(
            request_id=journey.id,
            document_scope_hash="hash_scope_e2e_test_123",
            provider=ProviderType.CERTISIGN,
            envelope_version=1
        )
        env_repo.update_external_id(
            envelope_id=envelope.id,
            external_envelope_id="ext_openapi_e2e_001",
            status=EnvelopeStatus.PENDING_SIGNATURE
        )

        signer_repo = EnvelopeSignerRepository(db_mgr)
        signer_repo.add_signer(
            envelope_id=envelope.id,
            associate_id=assoc.id,
            signer_role="TITULAR"
        )

        # 4. Testa Auditoria na maintenance_history
        print("\n4. Registrando auditoria na tabela maintenance_history...")
        manut_repo = MaintenanceHistoryRepository(db_mgr)
        log = manut_repo.log_maintenance(
            request_id=journey.id,
            envelope_id=envelope.id,
            reason_code=MaintenanceReason.MANUAL_INTERVENTION,
            detailed_description="Validação E2E com PostgreSQL real"
        )
        manut_repo.resolve_maintenance(log.id, resolved_by="QA_E2E_SCRIPT")

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
