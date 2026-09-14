"""
Módulo de Enumerações de Domínio do Microsserviço DocJourney.
Define todos os status, tipos de provedor, canais e motivos de manutenção do sistema.
Todos os identificadores e chaves seguem rigorosamente o padrão em inglês, com valores alinhados ao banco de dados.
"""

from enum import Enum


class JourneyStatus(str, Enum):
    """
    Representa o estado do ciclo de vida da jornada de solicitação recebida da esteira (Fluid/MongoDB).

    Valores:
        RECEIVED: Solicitação recebida e persistida no banco, aguardando início do processamento.
        IN_PROCESS: Automação em execução ativa (validações, clusterização e chamadas à API).
        COMPLETED: Todos os envelopes da solicitação foram gerados e disparados com sucesso.
        INTERVENTION: Ocorrência de pendências cadastrais ou erros negociais que requerem intervenção humana.
        ERROR: Erro crítico inesperado de infraestrutura durante o processamento.
    """
    RECEIVED = "RECEIVED"
    IN_PROCESS = "IN_PROCESS"
    COMPLETED = "COMPLETED"
    INTERVENTION = "INTERVENTION"
    ERROR = "ERROR"
    FAILED = "INTERVENTION"


class EnvelopeStatus(str, Enum):
    """
    Representa os estados possíveis de um envelope de assinatura na plataforma e no banco relacional.

    Valores:
        DRAFT: Envelope criado localmente, aguardando envio dos arquivos binários multipart.
        PENDING_SIGNATURE: Envelope registrado na OpenAPI e com links de assinatura gerados/enviados.
        COMPLETED: Todos os signatários obrigatórios assinaram os documentos do envelope.
        CANCELED: Envelope cancelado explicitamente antes da conclusão.
        REPLACED_CANCELED: Envelope descontinuado e substituído por uma nova versão devido a alterações no processo.
        EXPIRED: Envelope expirado após atingir a data limite de vigência (ex.: 60 dias).
        INTERVENTION: Envelope retido para conferência manual ou saneamento de dados.
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

    Valores:
        PENDING_LINK_DELIVERY: Signatário cadastrado, aguardando disparo do link de assinatura pelo canal.
        AWAITING_SIGNATURE: Link entregue com sucesso, aguardando a ação de assinatura pelo participante.
        SIGNED: Documento assinado com sucesso pelo participante.
        REJECTED: Assinatura recusada ativamente pelo participante.
    """
    PENDING_LINK_DELIVERY = "PENDING_LINK_DELIVERY"
    AWAITING_SIGNATURE = "AWAITING_SIGNATURE"
    SIGNED = "SIGNED"
    REJECTED = "REJECTED"


class DocumentStatus(str, Enum):
    """
    Representa o estado individual de um arquivo documental vinculado a um envelope.

    Valores:
        PENDING: Documento anexado, aguardando conclusão das assinaturas do envelope.
        SIGNED: Documento com todas as assinaturas colhidas e carimbo de tempo aplicado.
        EXPIRED: Documento cancelado por expiração temporal do envelope pai.
        CANCELED: Documento descartado devido ao cancelamento do envelope.
    """
    PENDING = "PENDING"
    SIGNED = "SIGNED"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"


class ProviderType(str, Enum):
    """
    Identifica a plataforma ou provedor externo de assinatura integrado.

    Valores:
        CERTISIGN: Provedor homologado Certisign via OpenAPI v2.
        ADESAO: Módulo interno de adesão eletrônica legado/especializado.
        PAS: Plataforma de Assinatura Sicredi.
    """
    CERTISIGN = "CERTISIGN"
    ADESAO = "ADESAO"
    PAS = "PAS"


class SignatureType(str, Enum):
    """
    Classifica a modalidade jurídica da assinatura a ser aplicada pelo participante.

    Valores:
        ELECTRONIC: Assinatura eletrônica simples/avançada (validação por e-mail, SMS ou WhatsApp).
        DIGITAL: Assinatura digital qualificada através de certificado ICP-Brasil (e-CPF / e-CNPJ).
    """
    ELECTRONIC = "ELETRONIC"
    DIGITAL = "DIGITAL"


class ValidationChannel(str, Enum):
    """
    Define o canal de comunicação para envio de tokens, links e autenticação do signatário.

    Valores:
        EMAIL: Envio do link de assinatura e autenticação via endereço de correio eletrônico.
        WHATSAPP: Disparo de notificações e segundo fator de autenticação via WhatsApp Enterprise.
        IN_PERSON: Coleta de assinatura presencial em agência cooperativa.
    """
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    IN_PERSON = "PRESENCIAL"


class MaintenanceReason(str, Enum):
    """
    Codifica o motivo da necessidade de manutenção, intervenção ou descontinuação de um envelope.

    Valores:
        DOC_NOT_AVAILABLE: Documento referenciado nos metadados não encontrado nos anexos.
        INVALID_SIGNER_DATA: Dados cadastrais do participante inválidos (CPF, telefone, e-mail).
        EXPIRED_60_DAYS: Envelope ultrapassou a janela temporal máxima de 60 dias sem assinatura.
        DOC_VERSION_CHANGE: Substituição seletiva motivada pela troca ou exclusão de versão de documento.
        SIGNER_CHANGE: Substituição seletiva decorrente da alteração ou troca de assinantes no processo.
        API_INTEGRATION_ERROR: Falha de comunicação ou rejeição de carga na integração com a OpenAPI.
    """
    DOC_NOT_AVAILABLE = "DOC_NOT_AVAILABLE"
    INVALID_SIGNER_DATA = "INVALID_SIGNER_DATA"
    EXPIRED_60_DAYS = "EXPIRED_60_DAYS"
    DOC_VERSION_CHANGE = "DOC_VERSION_CHANGE"
    SIGNER_CHANGE = "SIGNER_CHANGE"
    API_INTEGRATION_ERROR = "API_INTEGRATION_ERROR"
    CORRUPTED_DOCUMENT = "CORRUPTED_DOCUMENT"


# ==============================================================================
# Aliases para retrocompatibilidade com versões anteriores
# ==============================================================================
StatusJornada = JourneyStatus
StatusEnvelope = EnvelopeStatus
StatusSignatario = SignerStatus
StatusDocumento = DocumentStatus
ProviderEnum = ProviderType
TipoAssinaturaEnum = SignatureType
CanalValidacaoEnum = ValidationChannel
MotivoManutencaoEnum = MaintenanceReason


class AutomationNode(int, Enum):
    """
    Identifica os nós de ação da esteira Fluid / RPA para roteamento do processamento.

    Valores:
        CREATE_ENVELOPE (12): Criação inicial de envelopes e upload de documentos.
        UPDATE_SIGNATURE_METHOD (13): Troca de método/canal de assinatura (Presencial, WhatsApp, E-mail).
        CHANGE_SIGNERS (14): Substituição seletiva motivada por alteração de signatários.
        CHANGE_DOCUMENTS (15): Substituição seletiva motivada por alteração de documentos.
        CANCEL_ENVELOPE (16): Cancelamento explícito do envelope ativo.
    """
    CREATE_ENVELOPE = 12
    UPDATE_SIGNATURE_METHOD = 13
    CHANGE_SIGNERS = 14
    CHANGE_DOCUMENTS = 15
    CANCEL_ENVELOPE = 16


NodoAutomacao = AutomationNode

