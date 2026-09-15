"""
Módulo de Schemas Pydantic para Validação de Entrada e Saída da API REST (DocJourney).
Contratos de dados com tipagem estrita, documentação para Swagger OpenAPI e serialização JSON.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from microservico.domain.enums import (
    JourneyStatus,
    EnvelopeStatus,
    ProviderType,
    SignatureType,
    ValidationChannel,
    MaintenanceReason,
    SignerStatus,
    DocumentStatus
)


# ==============================================================================
# Schemas de Saúde e Métricas
# ==============================================================================

class HealthResponse(BaseModel):
    """Resposta do status de saúde do serviço."""
    status: str = Field(..., example="healthy")
    timestamp: datetime = Field(default_factory=datetime.now)
    database: str = Field(..., example="connected")
    rabbitmq: str = Field(..., example="connected")
    version: str = Field(default="2.0.0")


# ==============================================================================
# Schemas de Jornada (Journey / Request)
# ==============================================================================

class JourneyCreateRequest(BaseModel):
    """Payload para registro ou obtenção de uma jornada vinda do Fluid/MongoDB."""
    mongo_id: str = Field(..., description="ID único do documento no MongoDB (ex.: 65e89a...)", example="65e89a12bc98fe001a43d990")
    process_name: str = Field(default="Processo Genérico", description="Nome do processo de negócio", example="Abertura de Conta Corrente")
    process_number: int = Field(default=0, description="Número identificador do processo", example=10410)
    initial_id: Optional[str] = Field(default=None, description="ID da tarefa inicial em caso de retificação")
    fluid_payload: Dict[str, Any] = Field(default_factory=dict, description="Carga JSON íntegra vinda da esteira")


class JourneyResponse(BaseModel):
    """Representação serializada de uma jornada persistida."""
    id: UUID
    process_id: UUID
    mongo_id: str
    process_number: int
    initial_id: Optional[str] = None
    journey_status: JourneyStatus
    retry_count: int = 0
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ==============================================================================
# Schemas de Signatário e Documento (Embutidos no Envelope)
# ==============================================================================

class SignerCreateItem(BaseModel):
    """Dados de um signatário a ser vinculado ao envelope."""
    tax_id: str = Field(..., description="CPF ou CNPJ (apenas dígitos)", example="11158072937")
    name: str = Field(..., description="Nome completo do signatário", example="Pedro Henrique Lopes")
    email: Optional[str] = Field(default=None, example="pedro_hlopes@sicredi.com.br")
    phone: Optional[str] = Field(default=None, example="42999843189")
    role: str = Field(default="ASSINAR", example="ASSINAR")
    order: int = Field(default=1, example=1)
    signature_type: SignatureType = Field(default=SignatureType.ELECTRONIC)
    validation_channel: ValidationChannel = Field(default=ValidationChannel.WHATSAPP)


class DocumentCreateItem(BaseModel):
    """Metadados de um documento vinculado ao envelope."""
    template_id: str = Field(..., description="ID do template ou código do formulário", example="10410")
    name: str = Field(..., description="Nome do arquivo ou documento", example="Contrato_Adesao.pdf")
    document_hash: str = Field(..., description="Hash SHA-256 do arquivo binário")
    mime_type: str = Field(default="application/pdf")
    size_bytes: int = Field(default=0)


# ==============================================================================
# Schemas de Envelope
# ==============================================================================

class EnvelopeCreateRequest(BaseModel):
    """Payload para registro de um novo envelope na jornada."""
    request_id: UUID = Field(..., description="UUID da jornada pai")
    document_scope_hash: str = Field(..., description="Hash SHA256 do conjunto de documentos do envelope")
    envelope_version: int = Field(default=1, description="Versão do envelope (1 para criação inicial)")
    provider: ProviderType = Field(default=ProviderType.CERTISIGN)
    allow_signature_order: bool = Field(default=False)
    external_envelope_id: Optional[str] = Field(default=None, description="ID retornado pela OpenAPI externa")
    signers: List[SignerCreateItem] = Field(default_factory=list)
    documents: List[DocumentCreateItem] = Field(default_factory=list)


class EnvelopeResponse(BaseModel):
    """Representação serializada de um envelope persistido."""
    id: UUID
    request_id: UUID
    document_scope_hash: str
    envelope_version: int
    provider: ProviderType
    envelope_status: EnvelopeStatus
    external_envelope_id: Optional[str] = None
    allow_signature_order: bool = False
    is_altered: bool = False
    replaced_by_external_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    expired_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class EnvelopeStatusUpdateRequest(BaseModel):
    """Atualização de status e vínculo externo do envelope."""
    envelope_status: EnvelopeStatus
    external_envelope_id: Optional[str] = None
    comment: Optional[str] = None


class EnvelopeReplaceRequest(BaseModel):
    """Execução atômica de substituição seletiva de envelope."""
    old_envelope_id: UUID = Field(..., description="UUID do envelope a ser substituído/cancelado")
    new_document_scope_hash: str = Field(..., description="Hash dos novos documentos")
    reason_code: MaintenanceReason = Field(default=MaintenanceReason.DOC_VERSION_CHANGE)
    detailed_description: str = Field(..., example="Substituição seletiva por troca de versão documental")
    new_external_envelope_id: Optional[str] = None
    operator_name: str = Field(default="AUTOMATION_RPA")
    signers: List[SignerCreateItem] = Field(default_factory=list)
    documents: List[DocumentCreateItem] = Field(default_factory=list)


# ==============================================================================
# Schemas Específicos de Manutenção e Governança
# ==============================================================================

class MaintenanceCancelRequest(BaseModel):
    """Payload para cancelamento manual/administrativo de um envelope com auditoria."""
    envelope_id: UUID = Field(..., description="UUID do envelope a ser cancelado")
    reason_code: MaintenanceReason = Field(default=MaintenanceReason.DOC_NOT_AVAILABLE)
    detailed_description: str = Field(..., description="Motivo detalhado do cancelamento", example="Cancelamento solicitado pelo operador via esteira Fluid")
    canceled_by: str = Field(default="OPERATOR", example="HIGOR_CUSTODIO")


class MaintenanceExpireCheckResponse(BaseModel):
    """Resultado da rotina automática de varredura e expiração de envelopes."""
    expired_count: int = Field(..., description="Total de envelopes identificados e marcados como expirados")
    expired_envelope_ids: List[UUID] = Field(default_factory=list)
    processed_at: datetime = Field(default_factory=datetime.now)
    message: str


class MaintenanceHistoryResponse(BaseModel):
    """Registro individual de auditoria da tabela maintenance_history."""
    id: UUID
    request_id: Optional[UUID] = None
    envelope_id: Optional[UUID] = None
    reason_code: str
    detailed_description: Optional[str] = None
    resolved: bool
    resolved_by: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class MaintenanceResolveRequest(BaseModel):
    """Resolução de uma pendência de manutenção."""
    resolved_by: str = Field(default="OPERATOR", example="ADMIN_RPA")
    comment: Optional[str] = Field(default=None, example="Dados cadastrais saneados na origem")


class MaintenanceOverviewResponse(BaseModel):
    """Métricas operacionais consolidadas para governança do sistema."""
    total_journeys: int
    journeys_by_status: Dict[str, int]
    total_envelopes: int
    envelopes_by_status: Dict[str, int]
    unresolved_maintenance_incidents: int
    total_maintenance_incidents: int
    timestamp: datetime = Field(default_factory=datetime.now)
