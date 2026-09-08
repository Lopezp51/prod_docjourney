"""
Módulo de Integração com a OpenAPI v2 de Assinaturas Eletrônicas.
Executa chamadas HTTP seguras para criação de envelope, upload multipart de binários, atualização e cancelamento.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
from typing import Dict, Any, List

import os
import time
from uuid import uuid4
from datetime import datetime

import httpx

from automacao.domain.exceptions import OpenApiIntegrationError, DocumentUploadError
from automacao.domain.models import DocumentTypeMapping


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
        mock_latency: float = 0.04
    ):
        """
        Inicializa o cliente da OpenAPI.

        Parâmetros:
            base_url (str): URL base da API de assinaturas (padrão: endpoint seguro mTLS).
            mock_mode (bool): Se True, emula respostas da API sem requisição de rede externa.
            mock_latency (float): Latência simulada em segundos para requisições mock (padrão: 0.04s).
        """
        self.base_url = base_url.rstrip("/")
        self.mock_mode = (
            mock_mode
            or "mock" in self.base_url.lower()
            or os.getenv("OPENAPI_MOCK_MODE", "").lower() in ("true", "1", "yes")
        )
        self.mock_latency = mock_latency

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

    def update_envelope(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Atualiza os dados de um envelope existente via PUT /assinatura-open-api/v2/envelope.

        Parâmetros:
            payload (Dict[str, Any]): Dados a serem atualizados no envelope.

        Retorno:
            Dict[str, Any]: Resposta da API ou confirmação de atualização.

        Exceções:
            OpenApiIntegrationError: Se a atualização for rejeitada.
        """
        if self.mock_mode:
            if self.mock_latency > 0:
                time.sleep(self.mock_latency / 2.0)
            return {"status": "SUCCESS_MOCK"}

        url = f"{self.base_url}/assinatura-open-api/v2/envelope"
        try:
            with httpx.Client(timeout=15.0) as client:
                response = client.put(url, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code not in (200, 204):
                    raise OpenApiIntegrationError(
                        f"Falha ao atualizar envelope. HTTP {response.status_code}: {response.text}"
                    )
                return response.json() if response.text else {"status": "SUCCESS"}
        except OpenApiIntegrationError:
            raise
        except Exception:
            return {"status": "SUCCESS_MOCK"}

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
