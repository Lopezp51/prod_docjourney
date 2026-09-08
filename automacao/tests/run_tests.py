"""
Suíte de Testes Unitários da Automação RPA (DocJourney Automation).
Valida a pré-validação com acúmulo de pendências ('tudo de uma vez'),
a clusterização documental determinística e a execução ponta a ponta do fluxo RPA.
Nomes de métodos em inglês com docstrings em português.
"""

import sys
import os
import unittest

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from automacao.domain.models import SignerData, AttachmentData
from automacao.domain.exceptions import BulkValidationError
from automacao.core.validator import TaskPayloadValidator
from automacao.core.clusterizer import DocumentScopeClusterizer
from automacao.main import run_automation_task


class TestAutomationUnitFlow(unittest.TestCase):
    """
    Testes unitários dos motores de pré-validação, clusterização e execução do robô.
    """

    def setUp(self):
        """Inicializa as engines de validação e clusterização."""
        self.validator = TaskPayloadValidator()
        self.clusterizer = DocumentScopeClusterizer()

    def test_bulk_validation_accumulates_all_errors(self):
        """Valida que a Engine de Pré-Validação não faz 'fail-fast' e acumula todas as falhas numa única exceção."""
        signers = [
            SignerData(
                tax_id="111.111.111-00",  # CPF inválido
                name="Pedro Teste Erros",
                validation_channel="EMAIL",
                email="email_invalido_sem_arroba",  # Email inválido
                document_ids=["Doc Inexistente 123"]  # Doc não está nos anexos
            ),
            SignerData(
                tax_id="",  # CPF ausente
                name="Maria Teste Erros",
                validation_channel="WHATSAPP",
                phone="123",  # Telefone inválido (muito curto)
                document_ids=[]  # Nenhum documento vinculado
            )
        ]
        attachments = [
            AttachmentData(name="Doc Outro.pdf", hash_code="hash123", doc_type_id=765)
        ]

        with self.assertRaises(BulkValidationError) as context:
            self.validator.validate_task_data(signers, attachments)

        err = context.exception
        self.assertEqual(err.flow_error_code, "VAL_BULK_ERROR")
        # Deve ter acumulado ao menos 5 pendências
        self.assertGreaterEqual(len(err.errors), 5)

        # Verifica se o parecer HTML gerado contém as pendências formatadas
        parecer_html = err.to_fluid_parecer()
        self.assertIn("Olá Colega!", parecer_html)
        self.assertIn("<ul", parecer_html)
        self.assertIn("style='color: red;'", parecer_html)

    def test_document_scope_clusterization(self):
        """Valida a clusterização de signatários por interseção documental exata."""
        signers = [
            SignerData(tax_id="11158072937", name="Signatario A", document_ids=["765 - CCB", "613 - Seguro"]),
            SignerData(tax_id="08489951985", name="Signatario B", document_ids=["613 - Seguro", "765 - CCB"]),  # Ordem trocada
            SignerData(tax_id="02631353900", name="Signatario C", document_ids=["613 - Seguro"])  # Apenas 1 doc
        ]
        attachments = [
            AttachmentData(name="765 - CCB.pdf", hash_code="hash_ccb", doc_type_id=765),
            AttachmentData(name="613 - Seguro.pdf", hash_code="hash_seguro", doc_type_id=613)
        ]

        clusters = self.clusterizer.clusterize(signers, attachments)

        # Devem ser gerados exatamente 2 clusters
        self.assertEqual(len(clusters), 2)

        # Cluster 1 (Signatários A e B possuem exatamente o mesmo hash pois o hash é ordenado)
        cluster_ab = next(c for c in clusters if len(c.signers) == 2)
        self.assertEqual(len(cluster_ab.signers), 2)
        self.assertIn("Signatario A", [s.name for s in cluster_ab.signers])
        self.assertIn("Signatario B", [s.name for s in cluster_ab.signers])

        # Cluster 2 (Signatário C)
        cluster_c = next(c for c in clusters if len(c.signers) == 1)
        self.assertEqual(cluster_c.signers[0].name, "Signatario C")

    def test_end_to_end_automation_workflow_success(self):
        """Valida o fluxo completo de execução de uma tarefa válida do MongoDB."""
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

        result = run_automation_task(mongo_payload, use_sqlite=True)
        self.assertEqual(result["status"], "SUCESSO")
        self.assertEqual(result["process_number"], 1225591)
        self.assertEqual(result["clusters_count"], 1)

    def test_end_to_end_automation_workflow_bulk_error_catch(self):
        """Valida a captura centralizada de erro de pré-validação e geração do parecer."""
        payload_invalid = {
            "_id": {"$oid": "mongo_err_123"},
            "num_processo": 9999,
            "nome_processo": "Processo Erro",
            "infos_envio": {
                "atributos": {
                    "12905": [
                        [
                            {"id": 12909, "valor": "111.111.111-11"},  # CPF Inválido
                            {"id": 12910, "valor": "João Erro"},
                            {"id": 12857, "valor": '["Doc Ausente"]'},
                            {"id": 12912, "valor": "E-mail"},
                            {"id": 12913, "valor": "email_sem_arroba"}  # Email Inválido
                        ]
                    ]
                },
                "anexos": []
            }
        }

        result = run_automation_task(payload_invalid, use_sqlite=True)
        self.assertEqual(result["status"], "ERRO_FLUXO")
        self.assertEqual(result["codigo_erro"], "VAL_BULK_ERROR")
        self.assertIn("parecer_fluid", result)
        self.assertIn("style='color: red;'", result["parecer_fluid"])

    def test_corrupted_document_detection_and_fluid_parecer(self):
        """Valida que documentos corrompidos, vazios (0 bytes) ou sem hash disparam CorruptedDocumentError com orientações claras."""
        signers = [
            SignerData(
                tax_id="11158072937",
                name="Associado Teste",
                validation_channel="EMAIL",
                email="teste@sicredi.com.br",
                document_ids=["765 - CCB", "613 - Seguro", "999 - Quebrado"]
            )
        ]
        attachments = [
            # Caso 1: Instabilidade AWS / Fluid criou a vaga mas não atribuiu o arquivo (hash vazio)
            AttachmentData(name="765 - CCB.pdf", hash_code="", doc_type_id=765),
            # Caso 2: Arquivo vazio com 0 bytes
            AttachmentData(name="613 - Seguro.pdf", hash_code="hash_seguro_123", doc_type_id=613, file_size=0),
            # Caso 3: Arquivo com conteúdo que não é PDF (ex: erro XML da AWS)
            AttachmentData(
                name="999 - Quebrado.pdf",
                hash_code="hash_aws_err",
                doc_type_id=999,
                binary_content=b"<Error><Code>NoSuchKey</Code><Message>The specified key does not exist.</Message></Error>"
            )
        ]

        from automacao.domain.exceptions import CorruptedDocumentError
        with self.assertRaises(CorruptedDocumentError) as context:
            self.validator.validate_task_data(signers, attachments)

        err = context.exception
        self.assertEqual(err.flow_error_code, "CORRUPTED_DOCUMENT_ERROR")
        self.assertGreaterEqual(len(err.errors), 3)

        # Valida que identificou nominalmente os documentos quebrados
        errors_text = " ".join(err.errors)
        self.assertIn("765 - CCB.pdf", errors_text)
        self.assertIn("613 - Seguro.pdf", errors_text)
        self.assertIn("999 - Quebrado.pdf", errors_text)

        # Valida que o parecer HTML contém a instrução para o operador excluir e anexar novamente
        parecer_html = err.to_fluid_parecer()
        self.assertIn("corrompido(s), vazio(s) ou com falha de carregamento", parecer_html)
        self.assertIn("EXCLUA o(s) documento(s) corrompido(s)", parecer_html)
        self.assertIn("Anexe novamente", parecer_html)

    def test_end_to_end_corrupted_document_workflow(self):
        """Valida que uma tarefa com documento corrompido é tratada de forma elegante no workflow orquestrado."""
        payload_corrupted = {
            "_id": {"$oid": "mongo_corrupted_task"},
            "num_processo": 445566,
            "nome_processo": "Crédito Pessoal - Documento Quebrado",
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
                        "nome": "765 - CCB",
                        "hash": "hash_aws_corrompido",
                        "tipo_doc_id": 765,
                        "tamanho": 0,  # 0 bytes (arquivo vazio gerado por instabilidade AWS)
                        "extensao": "pdf"
                    }
                ]
            }
        }

        result = run_automation_task(payload_corrupted, use_sqlite=True)
        self.assertEqual(result["status"], "ERRO_FLUXO")
        self.assertEqual(result["codigo_erro"], "CORRUPTED_DOCUMENT_ERROR")
        self.assertIn("parecer_fluid", result)
        self.assertIn("765 - CCB", result["parecer_fluid"])
        self.assertIn("EXCLUA", result["parecer_fluid"])


if __name__ == "__main__":
    unittest.main()

