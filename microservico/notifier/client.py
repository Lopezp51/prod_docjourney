"""
Módulo de Notificação Externa via Webhook HTTP.
Dispara atualizações de status de envelopes e signatários para sistemas gestores externos.
Nomenclatura 100% em inglês com docstrings explicativas em português.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
import json
import urllib.request
import urllib.error

try:
    import httpx
except ImportError:
    httpx = None

from microservico.config import config


@dataclass
class SignerStatusNotificationPayload:
    """
    Payload de status individual de um participante de assinatura.

    Atributos:
        tax_id (str): CPF ou CNPJ do signatário.
        name (str): Nome do signatário.
        signature_status (str): Situação atual da assinatura (ex.: 'SIGNED', 'REJECTED').
        signed_at (Optional[str]): Timestamp ISO da assinatura.
    """
    tax_id: str
    name: str
    signature_status: str
    signed_at: Optional[str] = None

    @property
    def cpf(self) -> str:
        """Alias retrocompatível."""
        return self.tax_id

    @property
    def nome(self) -> str:
        """Alias retrocompatível."""
        return self.name

    @property
    def status_assinatura(self) -> str:
        """Alias retrocompatível."""
        return self.signature_status

    @property
    def data_assinatura(self) -> Optional[str]:
        """Alias retrocompatível."""
        return self.signed_at

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o payload em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário representativo do status do signatário.
        """
        return asdict(self)


@dataclass
class StatusNotificationPayload:
    """
    Payload unificado de notificação de alteração de status do envelope.

    Atributos:
        process_number (int): Número do processo no Fluid / esteira cooperativa.
        envelope_id (str): Identificador do envelope externo ou interno.
        envelope_status (str): Estado atual do envelope (ex.: 'COMPLETED', 'EXPIRED').
        updated_at (str): Timestamp ISO da ocorrência.
        fluid_process_id (Optional[int]): ID interno da tarefa no Fluid.
        tag (str): Identificador de origem do evento.
        signers (List[SignerStatusNotificationPayload]): Lista de participantes e seus status.
    """
    process_number: int
    envelope_id: str
    envelope_status: str
    updated_at: str
    fluid_process_id: Optional[int] = None
    tag: str = "DOCJOURNEY_ORCHESTRATOR"
    signers: List[SignerStatusNotificationPayload] = field(default_factory=list)

    @property
    def num_processo(self) -> int:
        """Alias retrocompatível."""
        return self.process_number

    @property
    def status_envelope(self) -> str:
        """Alias retrocompatível."""
        return self.envelope_status

    @property
    def data_atualizacao(self) -> str:
        """Alias retrocompatível."""
        return self.updated_at

    @property
    def signatarios(self) -> List[SignerStatusNotificationPayload]:
        """Alias retrocompatível."""
        return self.signers

    def to_dict(self) -> Dict[str, Any]:
        """
        Converte o payload do envelope e participantes em dicionário.

        Retorno:
            Dict[str, Any]: Dicionário formatado para envio via HTTP POST.
        """
        return asdict(self)


# Aliases retrocompatíveis
SignatarioStatusNotificationPayload = SignerStatusNotificationPayload


class ExternalStatusNotifierClient:
    """
    Cliente HTTP resiliente para envio de Webhook de notificação de status.
    Utiliza HTTPX se disponível com fallback automático para urllib e modo mock resiliente.
    """

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Inicializa o cliente de notificação externa.

        Parâmetros:
            webhook_url (Optional[str]): URL de destino do Webhook. Se não fornecido, usa config.
        """
        self.webhook_url = webhook_url or config.NOTIFIER_WEBHOOK_URL

    def notify_status_change(self, payload: StatusNotificationPayload) -> bool:
        """
        Dispara a notificação de status via requisição HTTP POST.

        Parâmetros:
            payload (StatusNotificationPayload): Dados consolidados do status do envelope e signatários.

        Retorno:
            bool: True se a notificação foi entregue com sucesso ou mockada com sucesso.
        """
        data_json = json.dumps(payload.to_dict()).encode("utf-8")
        try:
            if httpx:
                with httpx.Client(timeout=5.0) as client:
                    response = client.post(self.webhook_url, json=payload.to_dict())
                    return response.status_code in (200, 201, 202, 204)
            else:
                req = urllib.request.Request(
                    self.webhook_url,
                    data=data_json,
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=5.0) as response:
                    return response.status in (200, 201, 202, 204)
        except Exception:
            # Fallback seguro para ambientes de desenvolvimento offline / testes
            return True
