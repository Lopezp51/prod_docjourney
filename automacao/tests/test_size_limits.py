"""
Testes unitários para validação de limites de tamanho documental.
Garante que arquivos individuais não ultrapassem 20 MB e envelopes não ultrapassem 200 MB,
com suporte a customização fácil de limites.
"""

import unittest
from automacao.domain.models import SignerData, AttachmentData
from automacao.domain.exceptions import CorruptedDocumentError, BulkValidationError, EnvelopeClusterError
from automacao.core.validator import TaskPayloadValidator
from automacao.core.clusterizer import DocumentScopeClusterizer
from automacao.config import config


class TestDocumentSizeLimits(unittest.TestCase):
    """Suíte de testes para os limites operacionais de tamanho documental."""

    def setUp(self):
        self.validator = TaskPayloadValidator()
        self.clusterizer = DocumentScopeClusterizer()

    def test_default_config_limits(self):
        """Verifica se os limites padrão da configuração estão setados para 20 MB e 200 MB."""
        self.assertEqual(config.MAX_DOCUMENT_SIZE_MB, 20.0)
        self.assertEqual(config.MAX_ENVELOPE_SIZE_MB, 200.0)
        self.assertEqual(config.max_document_size_bytes, 20 * 1024 * 1024)
        self.assertEqual(config.max_envelope_size_bytes, 200 * 1024 * 1024)

    def test_file_size_exceeding_20mb_raises_corrupted_document_error(self):
        """Documento individual com mais de 20 MB deve ser rejeitado."""
        signers = [
            SignerData(
                tax_id="11158072937",
                name="Signatario Teste",
                email="teste@sicredi.com.br",
                document_ids=["DocPesado.pdf"]
            )
        ]
        # 21 MB = 21 * 1024 * 1024 bytes
        heavy_attachment = AttachmentData(
            name="DocPesado.pdf",
            hash_code="hash_doc_pesado",
            file_size=21 * 1024 * 1024,
            doc_type_id=10410
        )

        with self.assertRaises(CorruptedDocumentError) as ctx:
            self.validator.validate_task_data(signers, [heavy_attachment])

        error_msg = "; ".join(ctx.exception.errors)
        self.assertIn("excede o limite máximo permitido de 20 MB por arquivo", error_msg)

    def test_file_size_within_20mb_passes_validation(self):
        """Documento individual com até 20 MB deve passar pela validação."""
        signers = [
            SignerData(
                tax_id="11158072937",
                name="Signatario Teste",
                email="teste@sicredi.com.br",
                document_ids=["DocNormal.pdf"]
            )
        ]
        valid_attachment = AttachmentData(
            name="DocNormal.pdf",
            hash_code="hash_doc_normal",
            file_size=15 * 1024 * 1024,  # 15 MB
            doc_type_id=10410
        )

        # Não deve lançar exceção
        try:
            self.validator.validate_task_data(signers, [valid_attachment])
        except Exception as exc:
            self.fail(f"Validação falhou inesperadamente: {exc}")

    def test_envelope_size_exceeding_200mb_in_clusterizer(self):
        """Cluster de documentos que juntos somam mais de 200 MB deve ser rejeitado no clusterizer."""
        signers = [
            SignerData(
                tax_id="11158072937",
                name="Signatario Teste",
                email="teste@sicredi.com.br",
                document_ids=["Doc1.pdf", "Doc2.pdf", "Doc3.pdf"]
            )
        ]
        attachments = [
            AttachmentData(name="Doc1.pdf", hash_code="hash1", file_size=75 * 1024 * 1024),
            AttachmentData(name="Doc2.pdf", hash_code="hash2", file_size=75 * 1024 * 1024),
            AttachmentData(name="Doc3.pdf", hash_code="hash3", file_size=75 * 1024 * 1024),
        ]

        with self.assertRaises(EnvelopeClusterError) as ctx:
            self.clusterizer.clusterize(signers, attachments)

        self.assertIn("excedendo o limite máximo permitido de 200 MB por envelope", str(ctx.exception))

    def test_custom_limits_can_be_configured_easily(self):
        """Validador e clusterizer aceitam limites customizados facilmente."""
        custom_validator = TaskPayloadValidator(max_document_size_mb=5.0, max_envelope_size_mb=10.0)
        custom_clusterizer = DocumentScopeClusterizer(max_envelope_size_mb=10.0)

        signers = [
            SignerData(
                tax_id="11158072937",
                name="Signatario Custom",
                email="custom@sicredi.com.br",
                document_ids=["Doc6MB.pdf"]
            )
        ]
        # 6 MB excede o limite customizado de 5 MB
        att_6mb = AttachmentData(
            name="Doc6MB.pdf",
            hash_code="hash_6mb",
            file_size=6 * 1024 * 1024,
            doc_type_id=10410
        )

        with self.assertRaises(CorruptedDocumentError) as ctx:
            custom_validator.validate_task_data(signers, [att_6mb])

        self.assertIn("excede o limite máximo permitido de 5 MB por arquivo", "; ".join(ctx.exception.errors))


if __name__ == "__main__":
    unittest.main()
