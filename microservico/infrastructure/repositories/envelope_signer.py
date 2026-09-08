"""
Módulo do Repositório de Signatários de Envelopes (EnvelopeSignerRepository).
Gerencia os vínculos entre envelopes e associados participantes na tabela 'envelope_signers'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime
from typing import List
from uuid import UUID, uuid4

from microservico.domain.enums import SignatureType, SignerStatus, ValidationChannel
from microservico.domain.models import EnvelopeSignerModel
from microservico.infrastructure.repositories.base import BaseRepository


class EnvelopeSignerRepository(BaseRepository):
    """
    Repositório para signatários vinculados a envelopes (envelope_signers).

    Controla papéis, ordem de assinatura sequencial e canais de autenticação.
    """

    def _to_model(self, data: dict) -> EnvelopeSignerModel:
        """Converte dicionário de colunas para a entidade EnvelopeSignerModel."""
        return EnvelopeSignerModel(
            id=UUID(str(data["id"])),
            envelope_id=UUID(str(data["envelope_id"])),
            associate_id=UUID(str(data["associate_id"])),
            signer_role=data["signer_role"],
            signature_order=int(data.get("signature_order", 1)),
            signature_type=SignatureType(data["signature_type"]),
            validation_channel=ValidationChannel(data["validation_channel"]),
            signature_status=SignerStatus(data["signature_status"]),
            signed_at=data.get("signed_at"),
            rejected_at=data.get("rejected_at"),
            rejection_reason=data.get("rejection_reason"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def add_signer(
        self,
        envelope_id: UUID,
        associate_id: UUID,
        signer_role: str,
        signature_order: int = 1,
        signature_type: SignatureType = SignatureType.ELECTRONIC,
        validation_channel: ValidationChannel = ValidationChannel.EMAIL
    ) -> EnvelopeSignerModel:
        """
        Associa um signatário a um determinado envelope com seus canais e papéis.

        Parâmetros:
            envelope_id (UUID): ID do envelope pai.
            associate_id (UUID): ID do associado signatário.
            signer_role (str): Papel do signatário (Titular, Avalista, etc.).
            signature_order (int): Ordem de assinatura sequencial.
            signature_type (SignatureType): Eletrônica ou Digital.
            validation_channel (ValidationChannel): E-mail ou WhatsApp.

        Retorno:
            EnvelopeSignerModel: Registro do signatário associado.
        """
        new_id = uuid4()
        now = datetime.now()

        self.db_manager.execute(
            "INSERT INTO envelope_signers (id, envelope_id, associate_id, signer_role, signature_order, signature_type, validation_channel, signature_status, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                new_id,
                envelope_id,
                associate_id,
                signer_role,
                signature_order,
                signature_type,
                validation_channel,
                SignerStatus.PENDING_LINK_DELIVERY,
                now,
                now
            )
        )
        return EnvelopeSignerModel(
            id=new_id,
            envelope_id=envelope_id,
            associate_id=associate_id,
            signer_role=signer_role,
            signature_order=signature_order,
            signature_type=signature_type,
            validation_channel=validation_channel,
            signature_status=SignerStatus.PENDING_LINK_DELIVERY,
            created_at=now,
            updated_at=now
        )

    def list_by_envelope(self, envelope_id: UUID) -> List[EnvelopeSignerModel]:
        """
        Recupera todos os signatários associados a um envelope específico.

        Parâmetros:
            envelope_id (UUID): Identificador do envelope.

        Retorno:
            List[EnvelopeSignerModel]: Lista de signatários vinculados.
        """
        rows = self.db_manager.fetch_all(
            "SELECT * FROM envelope_signers WHERE envelope_id = %s ORDER BY signature_order ASC",
            (envelope_id,)
        )
        return [self._to_model(r) for r in rows]
