"""
Módulo do Repositório de Envelopes (EnvelopeRepository).
Gerencia a persistência, versionamento incremental e substituição seletiva na tabela 'envelopes'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime, timedelta
from typing import List, Optional
from uuid import UUID, uuid4

from microservico.domain.enums import EnvelopeStatus, ProviderType
from microservico.domain.models import EnvelopeModel
from microservico.infrastructure.repositories.base import BaseRepository


class EnvelopeRepository(BaseRepository):
    """
    Repositório para ciclo de vida e controle de envelopes (envelopes).

    Responsável pelo controle de versões, consulta otimizada sem N+1 e cancelamentos seletivos.
    """

    def _to_model(self, data: dict) -> EnvelopeModel:
        """Converte dicionário de colunas para a entidade de domínio EnvelopeModel."""
        return EnvelopeModel(
            id=UUID(str(data["id"])),
            request_id=UUID(str(data["request_id"])),
            document_scope_hash=data["document_scope_hash"],
            external_envelope_id=data.get("external_envelope_id"),
            envelope_version=int(data.get("envelope_version", 1)),
            provider=ProviderType(data["provider"]),
            envelope_status=EnvelopeStatus(data["envelope_status"]),
            allow_signature_order=bool(data.get("allow_signature_order", False)),
            sent_at=data.get("sent_at"),
            expired_at=data.get("expired_at"),
            completed_at=data.get("completed_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def get_by_id(self, envelope_id: UUID) -> Optional[EnvelopeModel]:
        """
        Recupera um envelope pelo identificador primário.

        Parâmetros:
            envelope_id (UUID): Identificador primário do envelope.

        Retorno:
            Optional[EnvelopeModel]: Objeto do envelope ou None.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM envelopes WHERE id = %s",
            (envelope_id,)
        )
        return self._to_model(row) if row else None

    def create_envelope(
        self,
        request_id: UUID,
        document_scope_hash: str,
        provider: ProviderType = ProviderType.CERTISIGN,
        envelope_version: int = 1,
        allow_signature_order: bool = False
    ) -> EnvelopeModel:
        """
        Cria um novo registro de envelope associado à jornada e ao hash de escopo documental.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai.
            document_scope_hash (str): Hash SHA256 único dos documentos do envelope.
            provider (ProviderType): Provedor de assinatura (Certisign, etc.).
            envelope_version (int): Número da versão do envelope.
            allow_signature_order (bool): Permite ordenamento sequencial de assinaturas.

        Retorno:
            EnvelopeModel: Instância do envelope persistido.
        """
        new_id = uuid4()
        now = datetime.now()
        expiration = now + timedelta(days=60)

        self.db_manager.execute(
            "INSERT INTO envelopes (id, request_id, document_scope_hash, envelope_version, provider, envelope_status, allow_signature_order, sent_at, expired_at, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                new_id,
                request_id,
                document_scope_hash,
                envelope_version,
                provider,
                EnvelopeStatus.DRAFT,
                allow_signature_order,
                now,
                expiration,
                now,
                now
            )
        )
        created = self.get_by_id(new_id)
        return created if created is not None else EnvelopeModel(
            id=new_id,
            request_id=request_id,
            document_scope_hash=document_scope_hash,
            envelope_version=envelope_version,
            provider=provider,
            envelope_status=EnvelopeStatus.DRAFT,
            allow_signature_order=allow_signature_order,
            sent_at=now,
            expired_at=expiration,
            created_at=now,
            updated_at=now
        )

    def get_active_by_request_and_hash(
        self,
        request_id: UUID,
        document_scope_hash: str
    ) -> Optional[EnvelopeModel]:
        """
        Localiza um envelope ativo correspondente ao escopo documental exato de uma solicitação.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai.
            document_scope_hash (str): Hash SHA256 do escopo documental.

        Retorno:
            Optional[EnvelopeModel]: Envelope ativo correspondente ou None.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM envelopes WHERE request_id = %s AND document_scope_hash = %s "
            "AND envelope_status NOT IN ('CANCELED', 'REPLACED_CANCELED', 'EXPIRED')",
            (request_id, document_scope_hash)
        )
        return self._to_model(row) if row else None

    def list_active_by_request(self, request_id: UUID) -> List[EnvelopeModel]:
        """
        Lista todos os envelopes atualmente ativos de uma solicitação sem incorrer em N+1 queries.

        Parâmetros:
            request_id (UUID): Identificador da solicitação.

        Retorno:
            List[EnvelopeModel]: Lista de envelopes ativos completos.
        """
        rows = self.db_manager.fetch_all(
            "SELECT * FROM envelopes WHERE request_id = %s "
            "AND envelope_status NOT IN ('CANCELED', 'REPLACED_CANCELED', 'EXPIRED') "
            "ORDER BY envelope_version ASC",
            (request_id,)
        )
        return [self._to_model(row) for row in rows]

    def get_max_version_by_request(self, request_id: UUID) -> int:
        """
        Calcula a versão máxima de envelopes registrada para uma determinada solicitação.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai.

        Retorno:
            int: Número da versão mais alta encontrada (0 se nenhuma existir).
        """
        row = self.db_manager.fetch_one(
            "SELECT COALESCE(MAX(envelope_version), 0) as max_v FROM envelopes WHERE request_id = %s",
            (request_id,)
        )
        if not row:
            return 0
        return int(row.get("max_v", 0))

    def update_external_id(
        self,
        envelope_id: UUID,
        external_envelope_id: str,
        status: EnvelopeStatus = EnvelopeStatus.PENDING_SIGNATURE
    ) -> None:
        """
        Atualiza o ID retornado pela API externa e muda o status do envelope.

        Parâmetros:
            envelope_id (UUID): Identificador do envelope no banco.
            external_envelope_id (str): ID gerado pela OpenAPI externa.
            status (EnvelopeStatus): Novo status (padrão: PENDING_SIGNATURE).
        """
        now = datetime.now()
        self.db_manager.execute(
            "UPDATE envelopes SET external_envelope_id = %s, envelope_status = %s, updated_at = %s WHERE id = %s",
            (external_envelope_id, status, now, envelope_id)
        )

    def mark_replaced_cancelled(self, envelope_id: UUID) -> None:
        """
        Marca um envelope anterior como substituído e cancelado em virtude de nova versão.

        Parâmetros:
            envelope_id (UUID): Identificador do envelope que foi substituído.
        """
        now = datetime.now()
        self.db_manager.execute(
            "UPDATE envelopes SET envelope_status = %s, updated_at = %s WHERE id = %s",
            (EnvelopeStatus.REPLACED_CANCELED, now, envelope_id)
        )

    def list_expired_over_60_days(self) -> List[EnvelopeModel]:
        """
        Localiza envelopes pendentes cuja data de expiração foi ultrapassada em consulta única sem N+1.

        Retorno:
            List[EnvelopeModel]: Lista de envelopes expirados identificados.
        """
        now = datetime.now()
        rows = self.db_manager.fetch_all(
            "SELECT * FROM envelopes WHERE envelope_status = 'PENDING_SIGNATURE' AND expired_at <= %s",
            (now,)
        )
        return [self._to_model(row) for row in rows]
