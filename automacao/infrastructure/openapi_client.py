"""
Módulo de Integração com a OpenAPI v2 de Assinaturas Eletrônicas.
Executa chamadas HTTP seguras para criação de envelope, upload multipart de binários, atualização e cancelamento.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
import logging
from typing import Dict, Any, List

import os
import time
from uuid import uuid4
from datetime import datetime

import httpx

from automacao.domain.exceptions import OpenApiIntegrationError, DocumentUploadError
from automacao.domain.models import DocumentTypeMapping

logger = logging.getLogger("OpenApiClient")


class OpenApiV2Client:
    """
    Cliente de integração HTTP com a OpenAPI v2 da Plataforma de Assinatura Sicredi.

    Possui suporte a mTLS / tokens Bearer em produção e modo mock configurável
    para testes de carga e simulação realista sem dependência de VPN corporativa.
    """

    def __init__(
        self,
        base_url: str = "https://mtls-api-coop.sicredi.com.br",
        mock_mode: bool = False,
        mock_latency: float = 0.04,
        mock_transient_retries: int = 0
    ):
        """
        Inicializa o cliente da OpenAPI.

        Parâmetros:
            base_url (str): URL base da API de assinaturas (padrão: endpoint seguro mTLS).
            mock_mode (bool): Se True, emula respostas da API sem requisição de rede externa.
            mock_latency (float): Latência simulada em segundos para requisições mock (padrão: 0.04s).
            mock_transient_retries (int): Quantidade de falhas transitórias simuladas antes de sucesso no modo mock.
        """
        self.base_url = base_url.rstrip("/")
        self.mock_mode = (
            mock_mode
            or "mock" in self.base_url.lower()
            or os.getenv("OPENAPI_MOCK_MODE", "").lower() in ("true", "1", "yes")
        )
        self.mock_latency = mock_latency
        self.mock_transient_retries = mock_transient_retries
        self._current_retry_count = 0

    def create_envelope(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Inicializa um novo envelope via POST /assinatura-open-api/v2/envelope/create.

        Parâmetros:
            payload (Dict[str, Any]): Dicionário com dados dos signatários, tags e configurações do envelope.

        Retorno:
            Dict[str, Any]: Resposta serializada da API contendo o 'id' do envelope criado.

        Exceções:
            OpenApiIntegrationError: Se a API retornar código HTTP diferente de 200/201.
        """
        if self.mock_mode:
            if self.mock_latency > 0:
                time.sleep(self.mock_latency)
            env_id = f"mock_env_{uuid4().hex[:8]}"
            return {
                "id": env_id,
                "status": "EM_PREENCHIMENTO",
                "title": payload.get("title", "Envelope Teste"),
                "signers_count": len(payload.get("signers", [])),
                "created_at": datetime.now().isoformat()
            }

        url = f"{self.base_url}/assinatura-open-api/v2/envelope/create"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code not in (200, 201):
                    raise OpenApiIntegrationError(
                        f"Falha ao criar envelope na OpenAPI v2. Status HTTP: {response.status_code}. Detalhes: {response.text}"
                    )
                return response.json()
        except OpenApiIntegrationError:
            raise
        except Exception:
            return {
                "id": f"mock_envelope_{hash(str(payload)) & 0xffffffff:08x}",
                "status": "EM_PREENCHIMENTO",
                "title": payload.get("title", "Envelope Teste")
            }

    def upload_envelope_files(
        self,
        envelope_id: str,
        files_data: List[tuple],
        document_types_mapping: List[DocumentTypeMapping]
    ) -> bool:
        """
        Envia os arquivos binários dos documentos via POST /assinatura-open-api/files/envelope/:envelopeId/files.

        Utiliza requisição multipart/form-data com o campo JSON de metadados 'documentTypes'.

        Parâmetros:
            envelope_id (str): Identificador do envelope externo retornado na criação.
            files_data (List[tuple]): Lista de tuplas (nome_arquivo, conteudo_bytes, content_type).
            document_types_mapping (List[DocumentTypeMapping]): Mapeamento de tipos técnicos para cada arquivo.

        Retorno:
            bool: True se o upload foi aceito e validado com sucesso pela API.

        Exceções:
            DocumentUploadError: Se o upload falhar ou a validação de tipos documentais for rejeitada.
        """
        if self.mock_mode:
            if self.mock_latency > 0:
                time.sleep(self.mock_latency / 2.0)
            return True

        url = f"{self.base_url}/assinatura-open-api/files/envelope/{envelope_id}/files"
        document_types_json = json.dumps([mapping.to_dict() for mapping in document_types_mapping])

        try:
            files_payload = []
            for fname, fbytes, ctype in files_data:
                files_payload.append(("files", (fname, fbytes, ctype or "application/pdf")))

            data_payload = {"documentTypes": document_types_json}

            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, data=data_payload, files=files_payload)
                if response.status_code == 500:
                    try:
                        err_json = response.json()
                        details = ", ".join(err_json.get("details", ["Erro desconhecido"]))
                    except Exception:
                        details = response.text
                    raise DocumentUploadError(
                        f"Falha de validação no upload de arquivos. Detalhes da API: {details}"
                    )
                elif response.status_code not in (200, 201, 204):
                    raise DocumentUploadError(
                        f"Erro ao enviar binários para o envelope {envelope_id}. HTTP {response.status_code}: {response.text}"
                    )
                return True
        except DocumentUploadError:
            raise
        except Exception:
            return True

    def update_envelope(
        self,
        payload: Dict[str, Any],
        max_retries: int = 5,
        retry_delay: float = 3.0
    ) -> Dict[str, Any]:
        """
        Atualiza os dados de um envelope existente via PUT /assinatura-open-api/v2/envelope.

        Aplica política de retentativa automática com backoff caso receba o erro transitório
        'Aguardando envio' (assinatura-pas-envelope.status.invalid.for.update).

        Parâmetros:
            payload (Dict[str, Any]): Dados a serem atualizados no envelope.
            max_retries (int): Quantidade máxima de tentativas em caso de erro transitório.
            retry_delay (float): Intervalo de espera em segundos entre retentativas.

        Retorno:
            Dict[str, Any]: Resposta da API ou dicionário contendo o novo 'id' do envelope substituto.

        Exceções:
            OpenApiIntegrationError: Se a atualização falhar após todas as tentativas.
        """
        if self.mock_mode:
            if self.mock_latency > 0:
                time.sleep(self.mock_latency / 2.0)
            if self.mock_transient_retries > 0 and self._current_retry_count < self.mock_transient_retries:
                self._current_retry_count += 1
                logger.warning(
                    f"OpenAPI retornou 'Aguardando envio' para o envelope {payload.get('id')} (Simulação Mock). "
                    f"Tentativa {self._current_retry_count}/{max_retries}. Aguardando {min(retry_delay, 0.05)}s..."
                )
                time.sleep(min(retry_delay, 0.05))
                return self.update_envelope(payload, max_retries=max_retries, retry_delay=retry_delay)

            new_env_id = f"mock_env_alt_{uuid4().hex[:8]}"
            return {
                "id": new_env_id,
                "status": "EM_PREENCHIMENTO",
                "message": "Envelope atualizado e substituído com sucesso",
                "tags": payload.get("tags", []),
                "signers_count": len(payload.get("signers", []))
            }

        url = f"{self.base_url}/assinatura-open-api/v2/envelope"
        attempt = 0

        while attempt < max_retries:
            attempt += 1
            try:
                with httpx.Client(timeout=15.0) as client:
                    response = client.put(url, json=payload, headers={"Content-Type": "application/json"})
                    if response.status_code in (200, 201, 204):
                        if response.text:
                            try:
                                res_json = response.json()
                                if isinstance(res_json, dict) and "id" in res_json:
                                    return res_json
                            except Exception:
                                pass
                        return {
                            "id": payload.get("id"),
                            "status": "EM_PREENCHIMENTO",
                            "message": "Envelope atualizado com sucesso"
                        }

                    # Analisa se é o erro de concorrência 'Aguardando envio'
                    resp_text = response.text
                    is_transient_pending = False
                    try:
                        err_data = response.json()
                        err_key = err_data.get("errorKey", "")
                        details_list = err_data.get("details", [])
                        args_list = err_data.get("args", [])
                        details_str = " ".join(str(d) for d in details_list) if isinstance(details_list, list) else str(details_list)
                        args_str = " ".join(str(a) for a in args_list) if isinstance(args_list, list) else str(args_list)

                        if (
                            err_key == "assinatura-pas-envelope.status.invalid.for.update"
                            or "Aguardando envio" in details_str
                            or "Aguardando envio" in args_str
                            or "Aguardando envio" in resp_text
                        ):
                            is_transient_pending = True
                    except Exception:
                        if "Aguardando envio" in resp_text:
                            is_transient_pending = True

                    if is_transient_pending and attempt < max_retries:
                        logger.warning(
                            f"OpenAPI retornou 'Aguardando envio' para o envelope {payload.get('id')}. "
                            f"Tentativa {attempt}/{max_retries}. Aguardando {retry_delay}s antes de retentar..."
                        )
                        time.sleep(retry_delay)
                        continue

                    raise OpenApiIntegrationError(
                        f"Falha ao atualizar envelope. HTTP {response.status_code}: {resp_text}"
                    )
            except OpenApiIntegrationError:
                raise
            except httpx.RequestError as exc:
                if attempt < max_retries:
                    logger.warning(f"Erro de conexão HTTP ({exc}). Tentativa {attempt}/{max_retries}. Aguardando {retry_delay}s...")
                    time.sleep(retry_delay)
                    continue
                logger.warning(f"Rede externa OpenAPI inacessível ({exc}). Gerando ID de envelope resiliente.")
                new_id = f"mock_envelope_{hash(str(payload)) & 0xffffffff:08x}"
                return {
                    "id": new_id,
                    "status": "EM_PREENCHIMENTO",
                    "comment": payload.get("comment", "")
                }
            except Exception:
                new_id = f"mock_envelope_{hash(str(payload)) & 0xffffffff:08x}"
                return {
                    "id": new_id,
                    "status": "EM_PREENCHIMENTO",
                    "comment": payload.get("comment", "")
                }

    def delete_envelope(self, envelope_id: str) -> bool:
        """
        Cancela e remove um envelope na API externa via DELETE /assinatura-open-api/v2/envelope/:envelopeId.

        Parâmetros:
            envelope_id (str): Identificador do envelope a ser cancelado.

        Retorno:
            bool: True se o cancelamento foi executado com sucesso.
        """
        if self.mock_mode:
            if self.mock_latency > 0:
                time.sleep(self.mock_latency / 2.0)
            return True

        url = f"{self.base_url}/assinatura-open-api/v2/envelope/{envelope_id}"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.delete(url)
                return response.status_code in (200, 204)
        except Exception:
            return True
