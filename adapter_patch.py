"""
adapter_patch.py: Camada de Adaptação Dinâmica de Schemas para a Automação RPA.
Mapeia campos defasados ou variáveis para o novo contrato exigido pelo Microsserviço/PAS.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


class SchemaPayloadAdapter:
    """Normalizador de payloads para comunicação segura com o Microsserviço."""

    @staticmethod
    def adapt_signer_to_service(signer_data: Dict[str, Any]) -> Dict[str, Any]:
        """Converte signatário da automação para o contrato do microsserviço."""
        return {
            "tax_id": str(signer_data.get("tax_id") or signer_data.get("cpf") or "").strip(),
            "name": str(signer_data.get("name") or signer_data.get("nome") or "").strip(),
            "email": signer_data.get("email"),
            "phone": signer_data.get("phone") or signer_data.get("telefone"),
            "role": signer_data.get("role") or signer_data.get("papel") or "ASSINAR",
            "order": int(signer_data.get("order") or signer_data.get("ordem") or 1),
            "signature_type": signer_data.get("signature_type") or "ELETRONIC",
            "validation_channel": signer_data.get("validation_channel") or "WHATSAPP"
        }

    @staticmethod
    def adapt_document_to_service(doc_data: Dict[str, Any]) -> Dict[str, Any]:
        """Converte anexo da automação para o contrato do microsserviço."""
        return {
            "template_id": str(doc_data.get("doc_type_id") or doc_data.get("template_id") or "10410"),
            "name": doc_data.get("name") or doc_data.get("nome") or "documento.pdf",
            "document_hash": doc_data.get("hash_code") or doc_data.get("hash") or "",
            "mime_type": "application/pdf",
            "size_bytes": doc_data.get("file_size") or doc_data.get("tamanho") or 0
        }

# Novos campos identificados para inclusão nos modelos da automação:
# Model AttachmentData:
#   mime_type: Optional[string] = None
#   size_bytes: Optional[integer] = None
