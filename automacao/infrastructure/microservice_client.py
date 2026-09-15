"""
Módulo de Cliente HTTP para Comunicação com a API do Microsserviço (DocJourney).
Permite que a automação RPA execute em máquinas Windows consumindo a persistência,
governança e rotas de manutenção sem conexão direta com o banco relacional PostgreSQL.
Possui fallback transparente para Mock em memória quando o servidor estiver offline (ideal para testes locais).
"""

import os
import logging
from typing import Dict, Any, List, Optional
from uuid import UUID, uuid4
from datetime import datetime

import httpx

from automacao.domain.enums import (
    JourneyStatus,
    EnvelopeStatus,
    ProviderType,
    MaintenanceReason
)

logger = logging.getLogger("MicroserviceApiClient")


class MicroserviceApiClient:
    """
    Cliente HTTP resiliente para consumir a API REST do Microsserviço DocJourney.
    Possui fallback automático para Mock em memória para testes offline.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: float = 30.0,
        client: Optional[httpx.Client] = None,
        fallback_to_mock: bool = True
    ):
        """
        Inicializa o cliente HTTP.

        Parâmetros:
            base_url (Optional[str]): URL base da API (padrão: MICROSERVICE_BASE_URL ou http://localhost:8000).
            timeout (float): Tempo limite para requisições em segundos.
            client (Optional[httpx.Client]): Instância customizada para testes ou mocks.
            fallback_to_mock (bool): Se True, opera em modo Mock quando o servidor estiver offline.
        """
        self.base_url = (base_url or os.getenv("MICROSERVICE_BASE_URL", "http://localhost:8000")).rstrip("/")
        self.timeout = timeout
        self._client = client or httpx.Client(base_url=self.base_url, timeout=self.timeout)
        self.fallback_to_mock = fallback_to_mock

        # Estado em memória para modo Mock
        self._is_mock_mode = False
        self._mock_journeys: Dict[str, Dict[str, Any]] = {}
        self._mock_envelopes: Dict[str, Dict[str, Any]] = {}
        self._mock_maintenance: List[Dict[str, Any]] = []

    def _activate_mock(self, reason: str = "") -> None:
        if not self._is_mock_mode:
            logger.info(f"Servidor API offline ({reason}). Ativando Mock em memória para a automação.")
            self._is_mock_mode = True

    def check_health(self) -> Dict[str, Any]:
        """Verifica a conectividade e saúde da API do microsserviço."""
        try:
            res = self._client.get("/health")
            res.raise_for_status()
            return res.json()
        except (httpx.ConnectError, httpx.TimeoutException) as err:
            if self.fallback_to_mock:
                self._activate_mock(str(err))
                return {"status": "mock_mode", "database": "mock_memory", "version": "2.0.0"}
            raise

    # ==========================================================================
    # Operações de Jornada (Journey)
    # ==========================================================================

    @staticmethod
    def _sanitize_for_json(data: Any) -> Any:
        """Remove objetos bytes e sanitiza estruturas para serialização JSON."""
        if isinstance(data, bytes):
            return "<binary_omitted>"
        if isinstance(data, dict):
            return {k: MicroserviceApiClient._sanitize_for_json(v) for k, v in data.items() if k not in ("binary_content", "conteudo_binario")}
        if isinstance(data, list):
            return [MicroserviceApiClient._sanitize_for_json(i) for i in data]
        return data

    def get_or_create_journey(
        self,
        mongo_id: str,
        process_name: str,
        process_number: int,
        fluid_payload: Optional[Dict[str, Any]] = None,
        initial_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Cria ou recupera uma jornada de forma idempotente pelo mongo_id."""
        clean_fluid = self._sanitize_for_json(fluid_payload or {})
        if not self._is_mock_mode:
            try:
                payload = {
                    "mongo_id": mongo_id,
                    "process_name": process_name,
                    "process_number": process_number,
                    "fluid_payload": clean_fluid,
                    "initial_id": initial_id
                }
                res = self._client.post("/api/v1/journeys", json=payload)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        # Modo Mock em memória
        if mongo_id in self._mock_journeys:
            return self._mock_journeys[mongo_id]

        new_journey = {
            "id": str(uuid4()),
            "process_id": str(uuid4()),
            "mongo_id": mongo_id,
            "process_number": process_number,
            "initial_id": initial_id,
            "journey_status": "RECEIVED",
            "retry_count": 1,
            "created_at": datetime.now().isoformat()
        }
        self._mock_journeys[mongo_id] = new_journey
        return new_journey

    def get_journey_by_mongo_id(self, mongo_id: str) -> Optional[Dict[str, Any]]:
        """Recupera uma jornada pelo mongo_id."""
        if not self._is_mock_mode:
            try:
                res = self._client.get(f"/api/v1/journeys/{mongo_id}")
                if res.status_code == 404:
                    return None
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        return self._mock_journeys.get(mongo_id)

    def update_journey_status(
        self,
        journey_id: str,
        status: JourneyStatus,
        details: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atualiza o estado de uma jornada."""
        status_str = status.value if hasattr(status, "value") else str(status)
        if not self._is_mock_mode:
            try:
                params = {"status_value": status_str}
                if details:
                    params["details"] = details
                res = self._client.patch(f"/api/v1/journeys/{journey_id}/status", params=params)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        for j in self._mock_journeys.values():
            if j["id"] == str(journey_id):
                j["journey_status"] = status_str
                j["details"] = details
        return {"message": f"Status atualizado para {status_str}"}

    def list_journey_envelopes(self, journey_id: str) -> List[Dict[str, Any]]:
        """Lista os envelopes ativos vinculados a uma determinada jornada."""
        if not self._is_mock_mode:
            try:
                res = self._client.get(f"/api/v1/journeys/{journey_id}/envelopes")
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        return [
            env for env in self._mock_envelopes.values()
            if env.get("request_id") == str(journey_id)
            and env.get("envelope_status") not in ("CANCELED", "REPLACED_CANCELED", "EXPIRED")
        ]

    # ==========================================================================
    # Operações de Envelope
    # ==========================================================================

    def create_envelope(
        self,
        request_id: str,
        document_scope_hash: str,
        envelope_version: int = 1,
        provider: ProviderType = ProviderType.CERTISIGN,
        allow_signature_order: bool = False,
        external_envelope_id: Optional[str] = None,
        signers: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Registra um novo envelope com documentos e signatários."""
        provider_str = provider.value if hasattr(provider, "value") else str(provider)
        if not self._is_mock_mode:
            try:
                payload = {
                    "request_id": str(request_id),
                    "document_scope_hash": document_scope_hash,
                    "envelope_version": envelope_version,
                    "provider": provider_str,
                    "allow_signature_order": allow_signature_order,
                    "external_envelope_id": external_envelope_id,
                    "signers": signers or [],
                    "documents": documents or []
                }
                res = self._client.post("/api/v1/envelopes", json=payload)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        env_id = str(uuid4())
        new_env = {
            "id": env_id,
            "request_id": str(request_id),
            "document_scope_hash": document_scope_hash,
            "envelope_version": envelope_version,
            "provider": provider_str,
            "envelope_status": "DRAFT",
            "external_envelope_id": external_envelope_id,
            "allow_signature_order": allow_signature_order,
            "created_at": datetime.now().isoformat()
        }
        self._mock_envelopes[env_id] = new_env
        return new_env

    def get_envelope(self, envelope_id: str) -> Optional[Dict[str, Any]]:
        """Recupera um envelope pelo seu ID."""
        if not self._is_mock_mode:
            try:
                res = self._client.get(f"/api/v1/envelopes/{envelope_id}")
                if res.status_code == 404:
                    return None
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        return self._mock_envelopes.get(str(envelope_id))

    def update_envelope_status(
        self,
        envelope_id: str,
        envelope_status: EnvelopeStatus,
        external_envelope_id: Optional[str] = None,
        comment: Optional[str] = None
    ) -> Dict[str, Any]:
        """Atualiza o status e/ou ID externo do envelope."""
        status_str = envelope_status.value if hasattr(envelope_status, "value") else str(envelope_status)
        if not self._is_mock_mode:
            try:
                payload = {
                    "envelope_status": status_str,
                    "external_envelope_id": external_envelope_id,
                    "comment": comment
                }
                res = self._client.patch(f"/api/v1/envelopes/{envelope_id}/status", json=payload)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        env = self._mock_envelopes.get(str(envelope_id))
        if env:
            env["envelope_status"] = status_str
            if external_envelope_id:
                env["external_envelope_id"] = external_envelope_id
            return env
        return {"id": str(envelope_id), "envelope_status": status_str}

    def replace_envelope(
        self,
        old_envelope_id: str,
        new_document_scope_hash: str,
        reason_code: MaintenanceReason = MaintenanceReason.DOC_VERSION_CHANGE,
        detailed_description: str = "",
        new_external_envelope_id: Optional[str] = None,
        operator_name: str = "AUTOMATION_RPA",
        signers: Optional[List[Dict[str, Any]]] = None,
        documents: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Executa a substituição seletiva via API."""
        reason_str = reason_code.value if hasattr(reason_code, "value") else str(reason_code)
        if not self._is_mock_mode:
            try:
                payload = {
                    "old_envelope_id": str(old_envelope_id),
                    "new_document_scope_hash": new_document_scope_hash,
                    "reason_code": reason_str,
                    "detailed_description": detailed_description,
                    "new_external_envelope_id": new_external_envelope_id,
                    "operator_name": operator_name,
                    "signers": signers or [],
                    "documents": documents or []
                }
                res = self._client.post(f"/api/v1/envelopes/{old_envelope_id}/replace", json=payload)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        old_env = self._mock_envelopes.get(str(old_envelope_id), {})
        old_env["envelope_status"] = "REPLACED_CANCELED"
        new_id = str(uuid4())
        new_env = {
            "id": new_id,
            "request_id": old_env.get("request_id", str(uuid4())),
            "document_scope_hash": new_document_scope_hash,
            "envelope_version": int(old_env.get("envelope_version", 1)) + 1,
            "provider": old_env.get("provider", "CERTISIGN"),
            "envelope_status": "PENDING_SIGNATURE",
            "external_envelope_id": new_external_envelope_id,
            "created_at": datetime.now().isoformat()
        }
        self._mock_envelopes[new_id] = new_env
        return new_env

    # ==========================================================================
    # Operações de Governança e Manutenção
    # ==========================================================================

    def cancel_envelope_maintenance(
        self,
        envelope_id: str,
        reason_code: MaintenanceReason,
        detailed_description: str,
        canceled_by: str = "AUTOMATION_RPA"
    ) -> Dict[str, Any]:
        """Cancela um envelope usando a rota administrativa de manutenção com auditoria."""
        reason_str = reason_code.value if hasattr(reason_code, "value") else str(reason_code)
        if not self._is_mock_mode:
            try:
                payload = {
                    "envelope_id": str(envelope_id),
                    "reason_code": reason_str,
                    "detailed_description": detailed_description,
                    "canceled_by": canceled_by
                }
                res = self._client.post("/api/v1/maintenance/cancel", json=payload)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        env = self._mock_envelopes.get(str(envelope_id))
        if env:
            env["envelope_status"] = "CANCELED"
        return {
            "status": "SUCCESS",
            "message": f"Envelope {envelope_id} cancelado via Mock.",
            "maintenance_id": str(uuid4())
        }

    def trigger_expiration_check(self) -> Dict[str, Any]:
        """Aciona a rotina automática de expiração de envelopes vencidos."""
        if not self._is_mock_mode:
            try:
                res = self._client.post("/api/v1/maintenance/expire-check")
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        return {"expired_count": 0, "message": "Rotina mock executada."}

    def get_maintenance_history(
        self,
        reason_code: Optional[str] = None,
        resolved: Optional[bool] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Consulta logs de auditoria da tabela maintenance_history via API."""
        if not self._is_mock_mode:
            try:
                params = {"limit": limit}
                if reason_code:
                    params["reason_code"] = reason_code
                if resolved is not None:
                    params["resolved"] = resolved

                res = self._client.get("/api/v1/maintenance/history", params=params)
                res.raise_for_status()
                return res.json()
            except (httpx.ConnectError, httpx.TimeoutException) as err:
                if not self.fallback_to_mock:
                    raise
                self._activate_mock(str(err))

        return self._mock_maintenance[:limit]
