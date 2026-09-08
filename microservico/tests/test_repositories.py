"""
Suíte de Testes Unitários dos Repositórios do Microsserviço DocJourney.
Valida idempotência, criação de jornadas, substituição seletiva de envelopes e persistência.
Nomes de métodos e asserções 100% em inglês com docstrings em português.
"""

import sys
import os
import pytest
from datetime import datetime

# Adiciona a raiz do projeto no PYTHONPATH para execução via pytest ou python direto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.repositories import (
    AssociateRepository,
    ProcessRepository,
    JourneyRepository,
    EnvelopeRepository,
    MaintenanceHistoryRepository
)
from microservico.domain.enums import (
    JourneyStatus,
    EnvelopeStatus,
    ProviderType,
    MaintenanceReason
)
from microservico.notifier.client import (
    ExternalStatusNotifierClient,
    StatusNotificationPayload,
    SignerStatusNotificationPayload
)

# Carrega o DDL do PROD_schema.sql
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "PROD_schema.sql")


@pytest.fixture
def db_manager():
    """Fixture que inicializa um banco SQLite em memória com o PROD_schema.sql aplicado."""
    manager = DatabaseManager(use_sqlite=True)
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    manager.execute_schema_sql(schema_sql)
    return manager


def test_associate_repository_upsert_and_get(db_manager):
    """Testa a inserção e atualização idempotente (upsert) na tabela de associados."""
    repo = AssociateRepository(db_manager)
    tax_id = "11158072937"
    name = "Pedro Henrique Lopes"
    email = "pedro@sicredi.com.br"

    # 1. Inserção inicial
    associate = repo.upsert(tax_id=tax_id, name=name, email=email, phone="42999843189")
    assert associate is not None
    assert associate.tax_id == tax_id
    assert associate.name == name
    assert associate.email == email

    # 2. Atualização (Upsert com alteração de nome)
    updated = repo.upsert(tax_id=tax_id, name="Pedro Lopes Atualizado", email=email, phone="42999843189")
    assert updated.name == "Pedro Lopes Atualizado"

    # 3. Busca pelo CPF
    fetched = repo.get_by_tax_id(tax_id)
    assert fetched.name == "Pedro Lopes Atualizado"


def test_process_and_journey_idempotency(db_manager):
    """Testa a idempotência da criação de processos e jornadas por mongo_id."""
    proc_repo = ProcessRepository(db_manager)
    journey_repo = JourneyRepository(db_manager)

    # 1. Busca ou criação do processo
    proc = proc_repo.get_or_create(name="Solicitação de Crédito Comercial V2", description="Crédito Comercial")
    assert proc.id is not None

    # 2. Criação de jornada e verificação de idempotência
    mongo_id = "6a9b225987db9287e3dde60c"
    payload = {"num_processo": 1225591, "status": "Fluid"}

    journey1 = journey_repo.create_journey(
        process_id=proc.id,
        mongo_id=mongo_id,
        process_number=1225591,
        fluid_payload=payload
    )
    assert journey1 is not None
    assert journey1.status == JourneyStatus.RECEIVED

    # Segunda tentativa com o mesmo mongo_id deve retornar a mesma instância sem duplicar
    journey2 = journey_repo.create_journey(
        process_id=proc.id,
        mongo_id=mongo_id,
        process_number=1225591,
        fluid_payload=payload
    )
    assert journey1.id == journey2.id


def test_envelope_clustering_hash_and_replacement(db_manager):
    """Testa o versionamento incremental e a marcação de envelopes substituídos (REPLACED_CANCELED)."""
    proc_repo = ProcessRepository(db_manager)
    journey_repo = JourneyRepository(db_manager)
    env_repo = EnvelopeRepository(db_manager)

    proc = proc_repo.get_or_create(name="Renovação Seguros V2")
    journey = journey_repo.create_journey(
        process_id=proc.id,
        mongo_id="mongo_12345",
        process_number=1160705,
        fluid_payload={}
    )

    scope_hash = "a1b2c3d4e5f67890_hash_cluster_docs_1_2"

    # 1. Criação do envelope versão 1
    envelope1 = env_repo.create_envelope(
        request_id=journey.id,
        document_scope_hash=scope_hash,
        provider=ProviderType.CERTISIGN,
        envelope_version=1
    )
    assert envelope1.envelope_status == EnvelopeStatus.DRAFT
    assert envelope1.document_scope_hash == scope_hash

    # 2. Busca ativa pelo request_id + document_scope_hash
    active_env = env_repo.get_active_by_request_and_hash(journey.id, scope_hash)
    assert active_env is not None
    assert active_env.id == envelope1.id

    # 3. Atualização de ID externo da OpenAPI
    env_repo.update_external_id(envelope1.id, external_envelope_id="openapi_env_999", status=EnvelopeStatus.PENDING_SIGNATURE)
    updated_env = env_repo.get_by_id(envelope1.id)
    assert updated_env.external_envelope_id == "openapi_env_999"
    assert updated_env.envelope_status == EnvelopeStatus.PENDING_SIGNATURE

    # 4. Substituição Seletiva: Marca como REPLACED_CANCELED e cria versão 2
    env_repo.mark_replaced_cancelled(envelope1.id)
    cancelled_env = env_repo.get_by_id(envelope1.id)
    assert cancelled_env.envelope_status == EnvelopeStatus.REPLACED_CANCELED

    # Busca ativa por aquele hash agora deve retornar None
    assert env_repo.get_active_by_request_and_hash(journey.id, scope_hash) is None

    # Cria o novo envelope versão 2
    envelope2 = env_repo.create_envelope(
        request_id=journey.id,
        document_scope_hash=scope_hash,
        provider=ProviderType.CERTISIGN,
        envelope_version=2
    )
    assert envelope2.envelope_version == 2
    assert env_repo.get_active_by_request_and_hash(journey.id, scope_hash).id == envelope2.id


def test_maintenance_history(db_manager):
    """Testa o registro de ocorrências e saneamento no histórico de manutenção."""
    proc_repo = ProcessRepository(db_manager)
    journey_repo = JourneyRepository(db_manager)
    manut_repo = MaintenanceHistoryRepository(db_manager)

    proc = proc_repo.get_or_create(name="Processo Teste")
    journey = journey_repo.create_journey(proc.id, "mongo_manut", 100, {})

    # Loga erro de manutenção por expiração
    log = manut_repo.log_maintenance(
        request_id=journey.id,
        reason_code=MaintenanceReason.EXPIRED_60_DAYS,
        detailed_description="Envelope expirado sem conclusão após 60 dias."
    )
    assert log.resolved is False
    assert log.reason_code == MaintenanceReason.EXPIRED_60_DAYS

    # Saneia a ocorrência
    manut_repo.resolve_maintenance(log.id, resolved_by="AUTOMATION")


def test_external_status_notifier_client():
    """Testa o disparo e serialização do payload de notificação de status."""
    client = ExternalStatusNotifierClient()
    payload = StatusNotificationPayload(
        process_number=1225591,
        envelope_id="openapi_env_999",
        envelope_status="COMPLETED",
        updated_at=datetime.now().isoformat(),
        signers=[
            SignerStatusNotificationPayload(
                tax_id="11158072937",
                name="Pedro Henrique Lopes",
                signature_status="SIGNED",
                signed_at=datetime.now().isoformat()
            )
        ]
    )
    success = client.notify_status_change(payload)
    assert success is True
