"""
Suíte de Testes Automatizados da Automação RPA (Isolada com Mocks de API).
Valida o comportamento completo da automação RPA sem necessidade de banco de dados
nem de instâncias ativas do microsserviço ou OpenAPI externa.
"""

import unittest
from unittest.mock import MagicMock
from uuid import uuid4

from automacao.main import run_automation_task
from automacao.domain.enums import JourneyStatus, EnvelopeStatus, MaintenanceReason, AutomationNode
from automacao.infrastructure.microservice_client import MicroserviceApiClient
from automacao.infrastructure.openapi_client import OpenApiV2Client


class TestAutomationRPA(unittest.TestCase):
    """Testes unitários isolados do robô RPA."""

    def setUp(self):
        """Configura mocks de clientes externos."""
        self.mock_api_client = MagicMock(spec=MicroserviceApiClient)
        self.mock_openapi_client = MagicMock(spec=OpenApiV2Client)

        self.fake_journey_id = str(uuid4())
        self.fake_envelope_id = str(uuid4())

        # Configura respostas padrão do cliente do microsserviço
        self.mock_api_client.get_or_create_journey.return_value = {
            "id": self.fake_journey_id,
            "mongo_id": "test_mongo_123",
            "process_number": 10410,
            "journey_status": "RECEIVED"
        }
        self.mock_api_client.list_journey_envelopes.return_value = []
        self.mock_api_client.create_envelope.return_value = {
            "id": self.fake_envelope_id,
            "envelope_version": 1,
            "envelope_status": "DRAFT"
        }
        self.mock_api_client.update_envelope_status.return_value = {
            "id": self.fake_envelope_id,
            "envelope_status": "PENDING_SIGNATURE"
        }
        self.mock_api_client.update_journey_status.return_value = {"status": "SUCCESS"}
        self.mock_api_client.cancel_envelope_maintenance.return_value = {
            "status": "SUCCESS",
            "maintenance_id": str(uuid4())
        }
        self.mock_api_client.replace_envelope.return_value = {
            "id": str(uuid4()),
            "envelope_version": 2,
            "envelope_status": "PENDING_SIGNATURE"
        }

        # Configura respostas padrão da OpenAPI externa
        self.mock_openapi_client.create_envelope.return_value = {"id": "openapi_env_9988"}
        self.mock_openapi_client.upload_envelope_files.return_value = {"status": "UPLOAD_SUCCESS"}
        self.mock_openapi_client.update_envelope.return_value = {"id": "openapi_env_put_11"}
        self.mock_openapi_client.delete_envelope.return_value = {"status": "DELETED"}

    def test_01_successful_create_envelope_flow(self):
        """Valida fluxo de criação de envelope (Nodo 12) com dados válidos."""
        task_payload = {
            "_id": "65e89a12bc98fe001a43d990",
            "num_processo": 10410,
            "nome_processo": "Abertura Conta Corrente",
            "nodo": 12,
            "infos_envio": {
                "anexos": [
                    {
                        "nome": "656 - Contrato_Abertura.pdf",
                        "id_tipo_documento": 656,
                        "hash_sha256": "hash_abc_123",
                        "size": 2048,
                        "binary_content": b"%PDF-1.4 Mock Valid Document Content Over 32 Bytes Header"
                    }
                ],
                "atributos": {
                    "10410": [
                        {
                            "cpf": "11158072937",
                            "nome": "Pedro Henrique Lopes",
                            "papel": "TITULAR",
                            "ordem": 1,
                            "email": "pedro@sicredi.com.br",
                            "phone": "42999843189",
                            "tipo_assinatura": "ELETRONIC",
                            "canal_validacao": "WHATSAPP",
                            "documentos": ["656"]
                        }
                    ]
                }
            }
        }

        result = run_automation_task(
            task_payload=task_payload,
            api_client=self.mock_api_client,
            openapi_client=self.mock_openapi_client
        )

        self.assertEqual(result["status"], "SUCESSO")
        self.assertEqual(result["nodo"], 12)
        self.assertEqual(result["journey_id"], self.fake_journey_id)
        self.assertEqual(len(result["envelopes"]), 1)

        # Verifica chamadas ao cliente da API do Microsserviço
        self.mock_api_client.get_or_create_journey.assert_called_once()
        self.mock_api_client.create_envelope.assert_called_once()
        self.mock_api_client.update_envelope_status.assert_called()
        self.mock_api_client.update_journey_status.assert_called()

        # Verifica chamadas à OpenAPI externa
        self.mock_openapi_client.create_envelope.assert_called_once()
        self.mock_openapi_client.upload_envelope_files.assert_called_once()

    def test_02_validation_failure_creates_html_parecer(self):
        """Valida que erros cadastrais (ex.: CPF inválido) geram parecer HTML e reportam status FAILED."""
        task_payload = {
            "_id": "65e89a12bc98fe001a43d999",
            "num_processo": 10411,
            "nome_processo": "Abertura Conta Corrente",
            "nodo": 12,
            "infos_envio": {
                "anexos": [
                    {
                        "nome": "656 - Contrato.pdf",
                        "id_tipo_documento": 656,
                        "hash_sha256": "hash_valid",
                        "size": 1024,
                        "binary_content": b"%PDF-1.4 Mock Valid File Content For Integrity Check"
                    }
                ],
                "atributos": {
                    "10410": [
                        {
                            "cpf": "00000000000",  # CPF INVÁLIDO
                            "nome": "Nome Teste",
                            "papel": "TITULAR",
                            "ordem": 1,
                            "email": "invalido",
                            "phone": "000",
                            "tipo_assinatura": "ELETRONIC",
                            "canal_validacao": "EMAIL",
                            "documentos": ["656"]
                        }
                    ]
                }
            }
        }

        result = run_automation_task(
            task_payload=task_payload,
            api_client=self.mock_api_client,
            openapi_client=self.mock_openapi_client
        )

        self.assertEqual(result["status"], "ERRO_FLUXO")
        self.assertIn("parecer_fluid", result)
        self.assertIn("<br>", result["parecer_fluid"])
        self.assertIn("detalhes_erros", result)
        self.assertGreater(len(result["detalhes_erros"]), 0)

        # Comprova que a jornada foi marcada como FAILED na API
        self.mock_api_client.update_journey_status.assert_called_with(
            journey_id=self.fake_journey_id,
            status=JourneyStatus.FAILED,
            details=unittest.mock.ANY
        )

    def test_03_update_signature_method_flow(self):
        """Valida alteração de canal de assinatura (Nodo 13)."""
        # Simula existência de envelope ativo
        self.mock_api_client.list_journey_envelopes.return_value = [
            {
                "id": self.fake_envelope_id,
                "external_envelope_id": "openapi_env_old",
                "envelope_version": 1,
                "document_scope_hash": "scope_hash_1"
            }
        ]

        task_payload = {
            "_id": "65e89a12bc98fe001a43d990",
            "num_processo": 10410,
            "nome_processo": "Abertura Conta Corrente",
            "nodo": 13,  # ATUALIZAR_METODO_ASSINATURA
            "infos_envio": {
                "anexos": [],
                "atributos": {
                    "10410": [
                        {
                            "cpf": "11158072937",
                            "nome": "Pedro Henrique Lopes",
                            "papel": "TITULAR",
                            "ordem": 1,
                            "email": "pedro@sicredi.com.br",
                            "phone": "42999843189",
                            "tipo_assinatura": "ELETRONIC",
                            "canal_validacao": "PRESENCIAL",
                            "documentos": [656]
                        }
                    ]
                }
            }
        }

        result = run_automation_task(
            task_payload=task_payload,
            api_client=self.mock_api_client,
            openapi_client=self.mock_openapi_client
        )

        self.assertEqual(result["status"], "SUCESSO")
        self.assertEqual(result["nodo"], 13)
        self.mock_openapi_client.update_envelope.assert_called_once()
        self.mock_api_client.replace_envelope.assert_called_once()

    def test_04_cancel_envelope_flow(self):
        """Valida cancelamento explícito de envelope (Nodo 16)."""
        self.mock_api_client.list_journey_envelopes.return_value = [
            {
                "id": self.fake_envelope_id,
                "external_envelope_id": "openapi_to_cancel",
                "envelope_version": 1
            }
        ]

        task_payload = {
            "_id": "65e89a12bc98fe001a43d990",
            "num_processo": 10410,
            "nome_processo": "Abertura Conta",
            "nodo": 16,  # CANCELAR_ENVELOPE
            "motivo_cancelamento": "Desistência do associado"
        }

        result = run_automation_task(
            task_payload=task_payload,
            api_client=self.mock_api_client,
            openapi_client=self.mock_openapi_client
        )

        self.assertEqual(result["status"], "SUCESSO")
        self.assertEqual(result["nodo"], 16)
        self.mock_openapi_client.delete_envelope.assert_called_with("openapi_to_cancel")
        self.mock_api_client.cancel_envelope_maintenance.assert_called_once()


if __name__ == "__main__":
    unittest.main()
