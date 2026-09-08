"""
Módulo de Modelos de Domínio do Microsserviço DocJourney.
Contém as entidades de dados mapeadas para as tabelas relacionais do PostgreSQL.
Nomes de classes, métodos e atributos 100% em inglês, com docstrings detalhadas em português.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Any, Dict
from uuid import UUID, uuid4

from microservico.domain.enums import (
    JourneyStatus,
    EnvelopeStatus,
    SignerStatus,
    DocumentStatus,
    ProviderType,
    SignatureType,
    ValidationChannel,
    MaintenanceReason
)


@dataclass
class AssociateModel:
    """
    Representa o associado (Pessoa Física ou Jurídica) titular ou interveniente no sistema.

    Atributos:
        tax_id: CPF ou CNPJ único do associado (apenas dígitos ou formatado).
        name: Nome completo ou razão social da pessoa cadastrada.
        email: Endereço de correio eletrônico para notificações e assinaturas.
        phone: Número de telefone celular para validações via SMS ou WhatsApp.
        id: Identificador único universal (UUID) gerado automaticamente.
        created_at: Data e hora do registro inicial no banco.
        updated_at: Data e hora da última modificação cadastral.
    """
    tax_id: str
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def cpf_cnpj(self) -> str:
        """Alias para manter compatibilidade com scripts legados."""
        return self.tax_id

    @property
    def nome(self) -> str:
        """Alias para manter compatibilidade com scripts legados."""
        return self.name

    @property
    def telefone(self) -> Optional[str]:
        """Alias para manter compatibilidade com scripts legados."""
        return self.phone

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a instância do modelo em um dicionário serializável.

        Retorno:
            Dict[str, Any]: Dicionário com todas as chaves e valores da entidade.
        """
        return asdict(self)


@dataclass
class ProcessModel:
    """
    Representa a tipificação do processo da esteira de negócios (ex.: Crédito Comercial, Seguros).

    Atributos:
        name: Nome descritivo e único do tipo de processo.
        description: Detalhamento técnico ou negocial do objetivo do processo.
        active: Indicador se o processo está apto para orquestração automática.
        id: Identificador único universal (UUID).
        created_at: Data e hora de criação do processo.
        updated_at: Data e hora da última atualização do registro.
    """
    name: str
    description: Optional[str] = None
    active: bool = True
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def nome(self) -> str:
        """Alias retrocompatível."""
        return self.name

    @property
    def descricao(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.description

    @property
    def ativo(self) -> bool:
        """Alias retrocompatível."""
        return self.active

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o processo em dicionário serializável.

        Retorno:
            Dict[str, Any]: Dicionário representativo do processo.
        """
        return asdict(self)


@dataclass
class JourneyRequestModel:
    """
    Representa a solicitação de jornada documental recebida da esteira (MongoDB/Fluid).

    Atributos:
        process_id: Identificador do processo ao qual a solicitação pertence.
        mongo_id: ID do documento original persistido no MongoDB para garantia de idempotência.
        process_number: Número da pasta ou processo na esteira cooperativa (ex.: 1225591).
        fluid_payload: Cópia íntegra em formato JSON dos metadados recebidos da tarefa Fluid.
        initial_id: Identificador da solicitação inicial em caso de reprocessamento.
        status: Estado atual da jornada no ciclo de processamento (JourneyStatus).
        details: Mensagens adicionais ou pareceres resumidos de execução.
        executions: Contador de tentativas de processamento da mesma solicitação.
        id: Identificador único universal (UUID).
        created_at: Data e hora da criação da jornada.
        updated_at: Data e hora da última atualização da jornada.
    """
    process_id: UUID
    mongo_id: str
    process_number: int
    fluid_payload: Dict[str, Any]
    initial_id: Optional[str] = None
    status: JourneyStatus = JourneyStatus.RECEIVED
    details: Optional[str] = None
    executions: int = 1
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def id_processo(self) -> UUID:
        """Alias retrocompatível."""
        return self.process_id

    @property
    def num_processo(self) -> int:
        """Alias retrocompatível."""
        return self.process_number

    @property
    def payload_fluid(self) -> Dict[str, Any]:
        """Alias retrocompatível."""
        return self.fluid_payload

    @property
    def id_inicial(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.initial_id

    @property
    def detalhes(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.details

    @property
    def execucoes(self) -> int:
        """Alias retrocompatível."""
        return self.executions

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a solicitação em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário representativo da solicitação.
        """
        return asdict(self)


@dataclass
class EnvelopeModel:
    """
    Representa um envelope gerado pelo agrupamento exato de documentos e signatários.

    Atributos:
        request_id: Identificador da jornada de solicitação pai.
        document_scope_hash: Hash SHA256 determinístico correspondente à combinação única de documentos.
        external_envelope_id: Identificador retornado pela OpenAPI de assinaturas externas.
        envelope_version: Número da versão do envelope dentro da solicitação (incrementado em substituições).
        provider: Provedor de assinatura utilizado (ProviderType).
        envelope_status: Estado do ciclo de vida do envelope (EnvelopeStatus).
        allow_signature_order: Flag indicando se a ordem cronológica de assinatura é estrita.
        sent_at: Data e hora de envio dos documentos e disparo das assinaturas.
        expired_at: Data limite para conclusão das assinaturas (60 dias por padrão).
        completed_at: Data e hora em que todas as assinaturas foram concluídas.
        id: Identificador único universal (UUID).
        created_at: Data de criação do registro no banco.
        updated_at: Data da última modificação.
    """
    request_id: UUID
    document_scope_hash: str
    external_envelope_id: Optional[str] = None
    envelope_version: int = 1
    provider: ProviderType = ProviderType.CERTISIGN
    envelope_status: EnvelopeStatus = EnvelopeStatus.DRAFT
    allow_signature_order: bool = False
    sent_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def id_solicitacao(self) -> UUID:
        """Alias retrocompatível."""
        return self.request_id

    @property
    def hash_escopo_documentos(self) -> str:
        """Alias retrocompatível."""
        return self.document_scope_hash

    @property
    def id_envelope_externo(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.external_envelope_id

    @property
    def versao_envelope(self) -> int:
        """Alias retrocompatível."""
        return self.envelope_version

    @property
    def status_envelope(self) -> EnvelopeStatus:
        """Alias retrocompatível."""
        return self.envelope_status

    @property
    def permitir_ordem_assinatura(self) -> bool:
        """Alias retrocompatível."""
        return self.allow_signature_order

    @property
    def data_envio(self) -> Optional[datetime]:
        """Alias retrocompatível."""
        return self.sent_at

    @property
    def data_expiracao(self) -> Optional[datetime]:
        """Alias retrocompatível."""
        return self.expired_at

    @property
    def data_conclusao(self) -> Optional[datetime]:
        """Alias retrocompatível."""
        return self.completed_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o envelope em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário representativo do envelope.
        """
        return asdict(self)


@dataclass
class DocumentModel:
    """
    Representa um arquivo PDF anexado e vinculado a um determinado envelope.

    Atributos:
        envelope_id: Identificador do envelope pai ao qual o documento pertence.
        associate_id: Identificador do associado titular relacionado ao documento.
        file_name: Nome completo do arquivo original (ex.: '765 - CCB.pdf').
        source_hash: Hash de integridade ou identificador do anexo na esteira Fluid.
        configuration_id: Identificador opcional da regra de template configurada.
        document_type_id: Código numérico de classificação do documento na esteira Sicredi.
        extension: Extensão do arquivo (padrão: 'pdf').
        version: Versão do documento.
        status: Estado individual do documento (DocumentStatus).
        id: Identificador único universal (UUID).
        created_at: Data de inserção do documento.
        updated_at: Data da última modificação.
    """
    envelope_id: UUID
    associate_id: UUID
    file_name: str
    source_hash: str
    configuration_id: Optional[UUID] = None
    document_type_id: Optional[int] = None
    extension: str = "pdf"
    version: int = 1
    status: DocumentStatus = DocumentStatus.PENDING
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def id_envelope(self) -> UUID:
        """Alias retrocompatível."""
        return self.envelope_id

    @property
    def id_associado(self) -> UUID:
        """Alias retrocompatível."""
        return self.associate_id

    @property
    def nome_arquivo(self) -> str:
        """Alias retrocompatível."""
        return self.file_name

    @property
    def hash_origem(self) -> str:
        """Alias retrocompatível."""
        return self.source_hash

    @property
    def tipo_doc_id(self) -> Optional[int]:
        """Alias retrocompatível."""
        return self.document_type_id

    @property
    def extensao(self) -> str:
        """Alias retrocompatível."""
        return self.extension

    @property
    def versao(self) -> int:
        """Alias retrocompatível."""
        return self.version

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o documento em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário representativo do documento.
        """
        return asdict(self)


@dataclass
class EnvelopeSignerModel:
    """
    Representa a associação de um participante/signatário a um envelope com seus canais e papéis.

    Atributos:
        envelope_id: Identificador do envelope.
        associate_id: Identificador do associado participante.
        external_signer_id: Identificador retornado pela OpenAPI para este assinante.
        signer_role: Papel funcional do assinante (ex.: 'Titular', 'Avalista', 'Testemunha').
        signature_order: Ordem sequencial de assinatura do participante.
        signature_type: Modalidade jurídica (SignatureType.ELECTRONIC ou SignatureType.DIGITAL).
        validation_channel: Canal de envio e validação (ValidationChannel.EMAIL ou WHATSAPP).
        signing_url: Link único de acesso para realização da assinatura pelo participante.
        signature_status: Estado atual da assinatura do participante (SignerStatus).
        signed_at: Data e hora em que a assinatura foi concluída.
        id: Identificador único universal (UUID).
        created_at: Data de criação da vinculação.
        updated_at: Data da última modificação.
    """
    envelope_id: UUID
    associate_id: UUID
    external_signer_id: Optional[str] = None
    signer_role: Optional[str] = None
    signature_order: int = 1
    signature_type: SignatureType = SignatureType.ELECTRONIC
    validation_channel: ValidationChannel = ValidationChannel.EMAIL
    signing_url: Optional[str] = None
    signature_status: SignerStatus = SignerStatus.PENDING_LINK_DELIVERY
    signed_at: Optional[datetime] = None
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def id_envelope(self) -> UUID:
        """Alias retrocompatível."""
        return self.envelope_id

    @property
    def id_associado(self) -> UUID:
        """Alias retrocompatível."""
        return self.associate_id

    @property
    def id_signatario_externo(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.external_signer_id

    @property
    def papel_assinante(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.signer_role

    @property
    def ordem_assinatura(self) -> int:
        """Alias retrocompatível."""
        return self.signature_order

    @property
    def tipo_assinatura(self) -> SignatureType:
        """Alias retrocompatível."""
        return self.signature_type

    @property
    def canal_validacao(self) -> ValidationChannel:
        """Alias retrocompatível."""
        return self.validation_channel

    @property
    def link_assinatura(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.signing_url

    @property
    def status_assinatura(self) -> SignerStatus:
        """Alias retrocompatível."""
        return self.signature_status

    @property
    def data_assinatura(self) -> Optional[datetime]:
        """Alias retrocompatível."""
        return self.signed_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a associação de signatário em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário representativo do signatário no envelope.
        """
        return asdict(self)


@dataclass
class MaintenanceHistoryModel:
    """
    Registra ocorrências técnicas, manutenções, intervenções e substituições de envelopes.

    Atributos:
        request_id: Identificador da jornada de solicitação vinculada.
        reason_code: Código categorizador do motivo da manutenção (MaintenanceReason).
        envelope_id: Identificador do envelope afetado, se aplicável.
        detailed_description: Relatório explicativo ou mensagem detalhada do erro.
        resolved: Indicador de saneamento ou resolução da ocorrência.
        resolved_by: Identificador do operador ou robô responsável pela resolução.
        id: Identificador único universal (UUID).
        created_at: Data e hora do registro da ocorrência.
        updated_at: Data da última modificação do registro.
    """
    request_id: UUID
    reason_code: MaintenanceReason
    envelope_id: Optional[UUID] = None
    detailed_description: Optional[str] = None
    resolved: bool = False
    resolved_by: Optional[str] = None
    id: UUID = field(default_factory=uuid4)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def id_solicitacao(self) -> UUID:
        """Alias retrocompatível."""
        return self.request_id

    @property
    def id_envelope(self) -> Optional[UUID]:
        """Alias retrocompatível."""
        return self.envelope_id

    @property
    def motivo_codigo(self) -> MaintenanceReason:
        """Alias retrocompatível."""
        return self.reason_code

    @property
    def descricao_detalhada(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.detailed_description

    @property
    def resolvido(self) -> bool:
        """Alias retrocompatível."""
        return self.resolved

    @property
    def resolvido_por(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.resolved_by

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o registro de histórico de manutenção em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário representativo da ocorrência de manutenção.
        """
        return asdict(self)


# ==============================================================================
# Aliases para retrocompatibilidade com nomenclatura legada
# ==============================================================================
AssociadoModel = AssociateModel
ProcessoModel = ProcessModel
JornadaSolicitacaoModel = JourneyRequestModel
DocumentoModel = DocumentModel
EnvelopeSignatarioModel = EnvelopeSignerModel
HistoricoManutencaoModel = MaintenanceHistoryModel
