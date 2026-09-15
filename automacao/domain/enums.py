"""
Módulo de Enumerações de Domínio da Automação RPA DocJourney.
Define todos os status, tipos de provedor, canais e motivos de manutenção do sistema.
Totalmente autônomo e isolado do microsserviço.
"""

from enum import Enum


class JourneyStatus(str, Enum):
    """
    Representa o estado do ciclo de vida da jornada de solicitação recebida da esteira (Fluid/MongoDB).
    """
    RECEIVED = "RECEIVED"
    IN_PROCESS = "IN_PROCESS"
    COMPLETED = "COMPLETED"
    INTERVENTION = "INTERVENTION"
    ERROR = "ERROR"
    FAILED = "INTERVENTION"


class EnvelopeStatus(str, Enum):
    """
    Representa os estados possíveis de um envelope de assinatura na plataforma.
    """
    DRAFT = "DRAFT"
    PENDING_SIGNATURE = "PENDING_SIGNATURE"
    COMPLETED = "COMPLETED"
    CANCELED = "CANCELED"
    REPLACED_CANCELED = "REPLACED_CANCELED"
    ALTERADO = "ALTERADO"
    EXPIRED = "EXPIRED"
    INTERVENTION = "INTERVENTION"


class SignerStatus(str, Enum):
    """
    Representa a situação individual de cada signatário vinculado a um determinado envelope.
    """
    PENDING_LINK_DELIVERY = "PENDING_LINK_DELIVERY"
    AWAITING_SIGNATURE = "AWAITING_SIGNATURE"
    SIGNED = "SIGNED"
    REJECTED = "REJECTED"


class DocumentStatus(str, Enum):
    """
    Representa o estado individual de um arquivo documental vinculado a um envelope.
    """
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"


class ProviderType(str, Enum):
    """
    Identifica a plataforma ou provedor externo de assinatura integrado.
    """
    CERTISIGN = "CERTISIGN"
    ADESAO = "ADESAO"
    PAS = "PAS"


class SignatureType(str, Enum):
    """
    Classifica a modalidade jurídica da assinatura a ser aplicada pelo participante.
    """
    ELECTRONIC = "ELETRONIC"
    DIGITAL = "DIGITAL"


class ValidationChannel(str, Enum):
    """
    Define o canal de comunicação para envio de tokens, links e autenticação do signatário.
    """
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    IN_PERSON = "PRESENCIAL"


class MaintenanceReason(str, Enum):
    """
    Codifica o motivo da necessidade de manutenção, intervenção ou descontinuação de um envelope.
    """
    DOC_NOT_AVAILABLE = "DOC_NOT_AVAILABLE"
    INVALID_SIGNER_DATA = "INVALID_SIGNER_DATA"
    EXPIRED_60_DAYS = "EXPIRED_60_DAYS"
    DOC_VERSION_CHANGE = "DOC_VERSION_CHANGE"
    SIGNER_CHANGE = "SIGNER_CHANGE"
    API_INTEGRATION_ERROR = "API_INTEGRATION_ERROR"
    CORRUPTED_DOCUMENT = "CORRUPTED_DOCUMENT"
    MANUAL_INTERVENTION = "MANUAL_INTERVENTION"



class AutomationNode(int, Enum):
    """
    Identifica os nós de ação da esteira Fluid / RPA para roteamento do processamento.
    """
    CREATE_ENVELOPE = 12
    UPDATE_SIGNATURE_METHOD = 13
    CHANGE_SIGNERS = 14
    CHANGE_DOCUMENTS = 15
    CANCEL_ENVELOPE = 16


# Aliases para retrocompatibilidade
StatusJornada = JourneyStatus
StatusEnvelope = EnvelopeStatus
StatusSignatario = SignerStatus
StatusDocumento = DocumentStatus
ProviderEnum = ProviderType
TipoAssinaturaEnum = SignatureType
CanalValidacaoEnum = ValidationChannel
MotivoManutencaoEnum = MaintenanceReason
NodoAutomacao = AutomationNode
