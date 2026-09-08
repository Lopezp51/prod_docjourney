"""
Script de Execução da Suíte de Testes Unitários do Microsserviço DocJourney.
Executa verificações completas de repositórios, schema DDL, seed data e notificador externo.
Nomes de métodos em inglês com docstrings em português.
"""

import sys
import os
import unittest
from datetime import datetime

# Adiciona a raiz do projeto no PYTHONPATH
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
from microservico.infrastructure.initializer import initialize_database_if_empty

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "PROD_schema.sql")


class TestMicroserviceRepositories(unittest.TestCase):
    """
    Casos de teste unitários dos repositórios relacionais e serviços de infraestrutura.
    """

    def setUp(self):
        """Inicializa um banco SQLite em memória com o PROD_schema.sql antes de cada teste."""
        self.db_manager = DatabaseManager(use_sqlite=True)
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        self.db_manager.execute_schema_sql(schema_sql)

    def test_database_initialization_and_seed(self):
        """Valida se o inicializador cria as tabelas e insere os processos de catálogo com sucesso."""
        empty_db = DatabaseManager(use_sqlite=True)
        initialize_database_if_empty(empty_db)

        proc_repo = ProcessRepository(empty_db)
        p1 = proc_repo.get_or_create(name="Solicitação de Crédito Comercial V2")
        self.assertIsNotNone(p1.id)
        p2 = proc_repo.get_or_create(name="Renovação Seguros V2")
        self.assertIsNotNone(p2.id)

    def test_associate_repository_upsert_and_get(self):
        """Valida a inserção e atualização com idempotência no repositório de associados."""
        repo = AssociateRepository(self.db_manager)
        tax_id = "11158072937"
        name = "Pedro Henrique Lopes"
        email = "pedro@sicredi.com.br"

        associate = repo.upsert(tax_id=tax_id, name=name, email=email, phone="42999843189")
        self.assertIsNotNone(associate)
        self.assertEqual(associate.tax_id, tax_id)
        self.assertEqual(associate.name, name)
        self.assertEqual(associate.email, email)

        updated = repo.upsert(tax_id=tax_id, name="Pedro Lopes Atualizado", email=email, phone="42999843189")
        self.assertEqual(updated.name, "Pedro Lopes Atualizado")

        fetched = repo.get_by_tax_id(tax_id)
        self.assertEqual(fetched.name, "Pedro Lopes Atualizado")

    def test_process_and_journey_idempotency(self):
        """Valida se uma mesma solicitação (mongo_id) não gera duplicidades na base de dados."""
        proc_repo = ProcessRepository(self.db_manager)
        journey_repo = JourneyRepository(self.db_manager)

        proc = proc_repo.get_or_create(name="Solicitação de Crédito Comercial V2", description="Crédito Comercial")
        self.assertIsNotNone(proc.id)

        mongo_id = "6a9b225987db9287e3dde60c"
        payload = {"num_processo": 1225591, "status": "Fluid"}

        journey1 = journey_repo.create_journey(
            process_id=proc.id,
            mongo_id=mongo_id,
            process_number=1225591,
            fluid_payload=payload
        )
        self.assertIsNotNone(journey1)
        self.assertEqual(journey1.status, JourneyStatus.RECEIVED)

        journey2 = journey_repo.create_journey(
            process_id=proc.id,
            mongo_id=mongo_id,
            process_number=1225591,
            fluid_payload=payload
        )
        self.assertEqual(journey1.id, journey2.id)

    def test_envelope_clustering_hash_and_replacement(self):
        """Valida o ciclo de vida e versionamento com substituição seletiva de envelopes."""
        proc_repo = ProcessRepository(self.db_manager)
        journey_repo = JourneyRepository(self.db_manager)
        env_repo = EnvelopeRepository(self.db_manager)

        proc = proc_repo.get_or_create(name="Renovação Seguros V2")
        journey = journey_repo.create_journey(
            process_id=proc.id,
            mongo_id="mongo_12345",
            process_number=1160705,
            fluid_payload={}
        )

        scope_hash = "a1b2c3d4e5f67890_hash_cluster_docs_1_2"

        envelope1 = env_repo.create_envelope(
            request_id=journey.id,
            document_scope_hash=scope_hash,
            provider=ProviderType.CERTISIGN,
            envelope_version=1
        )
        self.assertEqual(envelope1.envelope_status, EnvelopeStatus.DRAFT)
        self.assertEqual(envelope1.document_scope_hash, scope_hash)

        active_env = env_repo.get_active_by_request_and_hash(journey.id, scope_hash)
        self.assertIsNotNone(active_env)
        self.assertEqual(active_env.id, envelope1.id)

        env_repo.update_external_id(envelope1.id, external_envelope_id="openapi_env_999", status=EnvelopeStatus.PENDING_SIGNATURE)
        updated_env = env_repo.get_by_id(envelope1.id)
        self.assertEqual(updated_env.external_envelope_id, "openapi_env_999")
        self.assertEqual(updated_env.envelope_status, EnvelopeStatus.PENDING_SIGNATURE)

        env_repo.mark_replaced_cancelled(envelope1.id)
        cancelled_env = env_repo.get_by_id(envelope1.id)
        self.assertEqual(cancelled_env.envelope_status, EnvelopeStatus.REPLACED_CANCELED)

        self.assertIsNone(env_repo.get_active_by_request_and_hash(journey.id, scope_hash))

        envelope2 = env_repo.create_envelope(
            request_id=journey.id,
            document_scope_hash=scope_hash,
            provider=ProviderType.CERTISIGN,
            envelope_version=2
        )
        self.assertEqual(envelope2.envelope_version, 2)
        self.assertEqual(env_repo.get_active_by_request_and_hash(journey.id, scope_hash).id, envelope2.id)

    def test_maintenance_history(self):
        """Valida o registro e saneamento de ocorrências de manutenção no histórico."""
        proc_repo = ProcessRepository(self.db_manager)
        journey_repo = JourneyRepository(self.db_manager)
        manut_repo = MaintenanceHistoryRepository(self.db_manager)

        proc = proc_repo.get_or_create(name="Processo Teste")
        journey = journey_repo.create_journey(proc.id, "mongo_manut", 100, {})

        log = manut_repo.log_maintenance(
            request_id=journey.id,
            reason_code=MaintenanceReason.EXPIRED_60_DAYS,
            detailed_description="Envelope expirado sem conclusão após 60 dias."
        )
        self.assertFalse(log.resolved)
        self.assertEqual(log.reason_code, MaintenanceReason.EXPIRED_60_DAYS)

        manut_repo.resolve_maintenance(log.id, resolved_by="AUTOMATION")

    def test_external_status_notifier_client(self):
        """Valida o cliente de notificação externa e formatação de payload."""
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
        self.assertTrue(success)


if __name__ == "__main__":
    unittest.main()
