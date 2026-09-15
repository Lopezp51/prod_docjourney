"""
Suíte de Testes Automatizados da API FastAPI (DocJourney).
Valida todos os endpoints operacionais e rotas específicas de manutenção em ambiente isolado (SQLite em memória).
"""

import unittest
from uuid import uuid4
from fastapi.testclient import TestClient

from microservico.main import app
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.api.dependencies import set_db_manager


class TestDocJourneyAPI(unittest.TestCase):
    """Testes de integração para os endpoints REST do Microsserviço."""

    @classmethod
    def setUpClass(cls):
        """Inicializa banco SQLite em memória isolado para os testes."""
        cls.db_manager = DatabaseManager(use_sqlite=True)
        initialize_database_if_empty(cls.db_manager)
        set_db_manager(cls.db_manager)
        cls.client = TestClient(app)

    def test_01_health_check(self):
        """Verifica o endpoint /health."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["database"], "connected")

    def test_02_create_and_get_journey(self):
        """Valida criação idempotente e consulta de jornada por mongo_id."""
        mongo_id = f"test_mongo_{uuid4().hex[:8]}"
        payload = {
            "mongo_id": mongo_id,
            "process_name": "Abertura Conta Corrente Teste",
            "process_number": 9901,
            "initial_id": None,
            "fluid_payload": {"test": True}
        }
        # Criação
        res_create = self.client.post("/api/v1/journeys", json=payload)
        self.assertEqual(res_create.status_code, 201)
        created_data = res_create.json()
        self.assertEqual(created_data["mongo_id"], mongo_id)
        self.assertEqual(created_data["process_number"], 9901)
        journey_id = created_data["id"]

        # Busca por mongo_id
        res_get = self.client.get(f"/api/v1/journeys/{mongo_id}")
        self.assertEqual(res_get.status_code, 200)
        self.assertEqual(res_get.json()["id"], journey_id)

    def test_03_create_envelope_with_signers_and_docs(self):
        """Valida registro de envelope com participantes e documentos via API."""
        # Cria jornada pai
        mongo_id = f"test_env_mongo_{uuid4().hex[:8]}"
        res_j = self.client.post("/api/v1/journeys", json={
            "mongo_id": mongo_id,
            "process_name": "Processo Envelope Teste",
            "process_number": 1001
        })
        journey_id = res_j.json()["id"]

        # Cria envelope
        env_payload = {
            "request_id": journey_id,
            "document_scope_hash": "a1b2c3d4e5f6hash",
            "envelope_version": 1,
            "provider": "CERTISIGN",
            "external_envelope_id": "ext_env_12345",
            "signers": [
                {
                    "tax_id": "11122233344",
                    "name": "Signatario API Teste",
                    "email": "signatario@teste.com",
                    "phone": "41999998888",
                    "role": "TITULAR",
                    "order": 1,
                    "signature_type": "ELETRONIC",
                    "validation_channel": "WHATSAPP"
                }
            ],
            "documents": [
                {
                    "template_id": "10410",
                    "name": "Contrato.pdf",
                    "document_hash": "hash_doc_1",
                    "size_bytes": 1024
                }
            ]
        }
        res_env = self.client.post("/api/v1/envelopes", json=env_payload)
        self.assertEqual(res_env.status_code, 201)
        env_data = res_env.json()
        self.assertEqual(env_data["document_scope_hash"], "a1b2c3d4e5f6hash")
        self.assertEqual(env_data["envelope_version"], 1)
        self.assertEqual(env_data["external_envelope_id"], "ext_env_12345")

    def test_04_maintenance_cancel_envelope(self):
        """Valida rota de manutenção para cancelamento administrativo de envelope."""
        # Cria jornada e envelope
        res_j = self.client.post("/api/v1/journeys", json={
            "mongo_id": f"mongo_cancel_{uuid4().hex[:8]}",
            "process_name": "Cancel Test",
            "process_number": 1002
        })
        journey_id = res_j.json()["id"]

        res_env = self.client.post("/api/v1/envelopes", json={
            "request_id": journey_id,
            "document_scope_hash": "hash_cancel_test",
            "envelope_version": 1,
            "provider": "CERTISIGN"
        })
        env_id = res_env.json()["id"]

        # Executa cancelamento via rota de manutenção
        cancel_payload = {
            "envelope_id": env_id,
            "reason_code": "MANUAL_INTERVENTION",
            "detailed_description": "Cancelamento solicitado pelo operador QA",
            "canceled_by": "OPERADOR_TESTE"
        }
        res_cancel = self.client.post("/api/v1/maintenance/cancel", json=cancel_payload)
        self.assertEqual(res_cancel.status_code, 200)
        self.assertEqual(res_cancel.json()["status"], "SUCCESS")

        # Verifica se o envelope agora está CANCELED
        res_check = self.client.get(f"/api/v1/envelopes/{env_id}")
        self.assertEqual(res_check.json()["envelope_status"], "CANCELED")

    def test_05_maintenance_history_and_resolve(self):
        """Valida rota de consulta paginada ao histórico de manutenção e resolução."""
        # Consulta histórico
        res_hist = self.client.get("/api/v1/maintenance/history?limit=10")
        self.assertEqual(res_hist.status_code, 200)
        history_list = res_hist.json()
        self.assertIsInstance(history_list, list)
        self.assertGreaterEqual(len(history_list), 1)

        first_log = history_list[0]
        log_id = first_log["id"]

        # Resolve ocorrência via rota de manutenção
        res_resolve = self.client.patch(
            f"/api/v1/maintenance/history/{log_id}/resolve",
            json={"resolved_by": "GESTOR_OPERACIONAL", "comment": "Tudo corrigido"}
        )
        self.assertEqual(res_resolve.status_code, 200)
        self.assertEqual(res_resolve.json()["status"], "SUCCESS")

    def test_06_maintenance_expire_check(self):
        """Valida rotina de expiração automática de envelopes vencidos."""
        res_expire = self.client.post("/api/v1/maintenance/expire-check")
        self.assertEqual(res_expire.status_code, 200)
        data = res_expire.json()
        self.assertIn("expired_count", data)
        self.assertIn("message", data)

    def test_07_maintenance_overview_dashboard(self):
        """Valida métricas operacionais consolidadas do dashboard."""
        res_overview = self.client.get("/api/v1/maintenance/overview")
        self.assertEqual(res_overview.status_code, 200)
        data = res_overview.json()
        self.assertIn("total_journeys", data)
        self.assertIn("total_envelopes", data)
        self.assertIn("unresolved_maintenance_incidents", data)


if __name__ == "__main__":
    unittest.main()
