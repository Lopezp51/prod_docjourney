"""
Módulo de Modelos de Domínio da Automação RPA.
Define estruturas de dados para signatários, anexos, mapeamentos de tipos técnicos e clusters de envelopes.
Nomes de classes, métodos e atributos 100% em inglês com docstrings explicativas em português e suporte a aliases.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


@dataclass
class SignerData:
    """
    Representa os dados cadastrais e de assinatura de um signatário extraído do payload do processo.

    Atributos:
        tax_id (str): CPF ou CNPJ do participante.
        name (str): Nome completo ou razão social.
        order (int): Ordem de assinatura sequencial (padrão: 1).
        role (str): Papel do signatário (ex.: 'Signatário', 'Titular', 'Avalista').
        email (Optional[str]): Endereço de e-mail para envio de links e tokens.
        phone (Optional[str]): Telefone celular com DDD para validações por WhatsApp/SMS.
        signature_type (str): Tipo de assinatura ('ELETRONIC' ou 'DIGITAL').
        validation_channel (str): Canal de comunicação ('EMAIL' ou 'WHATSAPP').
        document_ids (List[str]): Lista de identificadores/nomes dos documentos vinculados para assinatura.
    """
    tax_id: str
    name: str
    order: int = 1
    role: str = "Signatário"
    email: Optional[str] = None
    phone: Optional[str] = None
    signature_type: str = "ELETRONIC"
    validation_channel: str = "EMAIL"
    document_ids: List[str] = field(default_factory=list)

    @property
    def cpf(self) -> str:
        """Alias retrocompatível."""
        return self.tax_id

    @property
    def nome(self) -> str:
        """Alias retrocompatível."""
        return self.name

    @property
    def ordem(self) -> int:
        """Alias retrocompatível."""
        return self.order

    @property
    def papel(self) -> str:
        """Alias retrocompatível."""
        return self.role

    @property
    def telefone(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.phone

    @property
    def tipo_assinatura(self) -> str:
        """Alias retrocompatível."""
        return self.signature_type

    @property
    def canal_validacao(self) -> str:
        """Alias retrocompatível."""
        return self.validation_channel

    @property
    def documentos_ids(self) -> List[str]:
        """Alias retrocompatível."""
        return self.document_ids

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte a estrutura do signatário em dicionário serializável.

        Retorno:
            Dict[str, Any]: Dicionário representativo do signatário.
        """
        return asdict(self)


@dataclass
class AttachmentData:
    """
    Representa os metadados e o conteúdo binário de um arquivo documental anexado na solicitação.

    Atributos:
        name (str): Nome do arquivo (ex.: '765 - CCB.pdf').
        hash_code (str): Hash de integridade ou identificador do anexo no repositório.
        doc_type_id (Optional[int]): Código numérico de tipo técnico do documento.
        extension (str): Extensão do arquivo (padrão: 'pdf').
        binary_content (Optional[bytes]): Conteúdo binário para upload multipart.
        file_size (Optional[int]): Tamanho do arquivo em bytes (se informado pela esteira).
        is_corrupted (bool): Flag indicando se o arquivo está corrompido ou quebrado.
        corruption_reason (Optional[str]): Motivo detalhado da corrupção ou falha de leitura.
    """
    name: str
    hash_code: str
    doc_type_id: Optional[int] = None
    extension: str = "pdf"
    binary_content: Optional[bytes] = None
    file_size: Optional[int] = None
    is_corrupted: bool = False
    corruption_reason: Optional[str] = None

    @property
    def nome(self) -> str:
        """Alias retrocompatível."""
        return self.name

    @property
    def hash(self) -> str:
        """Alias retrocompatível."""
        return self.hash_code

    @property
    def extensao(self) -> str:
        """Alias retrocompatível."""
        return self.extension

    @property
    def tipo_doc_id(self) -> Optional[int]:
        """Alias retrocompatível."""
        return self.doc_type_id

    @property
    def conteudo_binario(self) -> Optional[bytes]:
        """Alias retrocompatível."""
        return self.binary_content

    @property
    def tamanho(self) -> Optional[int]:
        """Alias retrocompatível para o tamanho do arquivo em bytes."""
        return self.file_size

    @property
    def is_corrompido(self) -> bool:
        """Alias retrocompatível para a flag de documento corrompido."""
        return self.is_corrupted

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte os dados do anexo em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário com metadados do arquivo.
        """
        return asdict(self)


# Alias retrocompatível
AnexoData = AttachmentData


@dataclass
class DocumentTypeItem:
    """
    Item individual de mapeamento de tipo de documento exigido no payload multipart da OpenAPI v2.

    Atributos:
        document_type (str): Código técnico do documento (ex.: 'DOCUMENT_TYPE_TTD_765').
        is_attachment (bool): Flag indicando se é anexo secundário.
    """
    document_type: str
    is_attachment: bool = False

    @property
    def documentType(self) -> str:
        """Alias camelCase para serialização."""
        return self.document_type

    @property
    def isAttachment(self) -> bool:
        """Alias camelCase para serialização."""
        return self.is_attachment


@dataclass
class DocumentTypeMapping:
    """
    Estrutura de associação entre o nome do arquivo físico e seus tipos documentais para a OpenAPI v2.

    Atributos:
        file_name (str): Nome do arquivo que está sendo enviado via multipart.
        document_types (List[DocumentTypeItem]): Lista de classificações técnicas aplicadas ao arquivo.
    """
    file_name: str
    document_types: List[DocumentTypeItem] = field(default_factory=list)

    @property
    def fileName(self) -> str:
        """Alias camelCase para serialização."""
        return self.file_name

    @property
    def documentType(self) -> List[DocumentTypeItem]:
        """Alias camelCase para compatibilidade com código anterior."""
        return self.document_types

    def to_dict(self) -> Dict[str, Any]:
        """
        Gera o dicionário no formato exato esperado pelo campo multipart 'documentTypes' da OpenAPI.

        Retorno:
            Dict[str, Any]: Objeto serializado compatível com o schema JSON da API.
        """
        return {
            "fileName": self.file_name,
            "documentType": [
                {"documentType": item.document_type, "isAttachment": item.is_attachment}
                for item in self.document_types
            ]
        }


@dataclass
class EnvelopeCluster:
    """
    Representa um cluster resultante do agrupamento exato entre Documentos e Signatários.

    Atributos:
        scope_hash (str): Hash SHA256 determinístico único que identifica o conjunto de documentos deste cluster.
        document_ids (List[str]): IDs ou nomes dos documentos associados a este grupo.
        signers (List[SignerData]): Lista de signatários que devem assinar este grupo de documentos.
        attachments (List[AttachmentData]): Objetos de anexo físico vinculados a este cluster.
    """
    scope_hash: str
    document_ids: List[str]
    signers: List[SignerData]
    attachments: List[AttachmentData]

    @property
    def hash_escopo(self) -> str:
        """Alias retrocompatível."""
        return self.scope_hash

    @property
    def documents(self) -> List[AttachmentData]:
        """Alias para attachments."""
        return self.attachments



    @property
    def documentos_ids(self) -> List[str]:
        """Alias retrocompatível."""
        return self.document_ids

    @property
    def signatarios(self) -> List[SignerData]:
        """Alias retrocompatível."""
        return self.signers

    @property
    def anexos(self) -> List[AttachmentData]:
        """Alias retrocompatível."""
        return self.attachments

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o cluster em dicionário serializável.

        Retorno:
            Dict[str, Any]: Dicionário representativo do cluster.
        """
        return asdict(self)
