"""
Módulo do Repositório de Documentos (DocumentRepository).
Gerencia os anexos e arquivos PDFs vinculados a envelopes na tabela 'documents'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4

from microservico.domain.enums import DocumentStatus
from microservico.domain.models import DocumentModel
from microservico.infrastructure.repositories.base import BaseRepository


class DocumentRepository(BaseRepository):
    """
    Repositório de documentos PDFs vinculados a envelopes (documents).

    Controla o vínculo entre envelopes, associados titulares e arquivos anexos.
    """

    def _to_model(self, data: dict) -> DocumentModel:
        """Converte dicionário de colunas para a entidade DocumentModel."""
        return DocumentModel(
            id=UUID(str(data["id"])),
            envelope_id=UUID(str(data["envelope_id"])),
            associate_id=UUID(str(data["associate_id"])),
            file_name=data["file_name"],
            source_hash=data["source_hash"],
            document_type_id=int(data["document_type_id"]) if data.get("document_type_id") is not None else None,
            extension=data.get("extension", "pdf"),
            status=DocumentStatus(data["status"]),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def add_document(
        self,
        envelope_id: UUID,
        associate_id: UUID,
        file_name: str,
        source_hash: str,
        document_type_id: Optional[int] = None,
        extension: str = "pdf"
    ) -> DocumentModel:
        """
        Vincula um arquivo documental a um envelope existente.

        Parâmetros:
            envelope_id (UUID): ID do envelope pai.
            associate_id (UUID): ID do associado titular.
            file_name (str): Nome do arquivo.
            source_hash (str): Hash de integridade original.
            document_type_id (Optional[int]): Código de classificação técnica do documento.
            extension (str): Extensão do arquivo (padrão: 'pdf').

        Retorno:
            DocumentModel: Entidade do documento registrada.
        """
        new_id = uuid4()
        now = datetime.now()

        self.db_manager.execute(
            "INSERT INTO documents (id, envelope_id, associate_id, file_name, source_hash, document_type_id, extension, status, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                new_id,
                envelope_id,
                associate_id,
                file_name,
                source_hash,
                document_type_id,
                extension,
                DocumentStatus.PENDING,
                now,
                now
            )
        )
        return DocumentModel(
            id=new_id,
            envelope_id=envelope_id,
            associate_id=associate_id,
            file_name=file_name,
            source_hash=source_hash,
            document_type_id=document_type_id,
            extension=extension,
            status=DocumentStatus.PENDING,
            created_at=now,
            updated_at=now
        )

    def list_by_envelope(self, envelope_id: UUID) -> List[DocumentModel]:
        """
        Recupera todos os documentos vinculados a um determinado envelope.

        Parâmetros:
            envelope_id (UUID): Identificador do envelope.

        Retorno:
            List[DocumentModel]: Lista de documentos pertencentes ao envelope.
        """
        rows = self.db_manager.fetch_all(
            "SELECT * FROM documents WHERE envelope_id = %s ORDER BY created_at ASC",
            (envelope_id,)
        )
        return [self._to_model(r) for r in rows]
