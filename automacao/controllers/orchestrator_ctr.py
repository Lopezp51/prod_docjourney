"""
Módulo do Controlador Orquestrador da Automação RPA.
Coordena a extração do payload do MongoDB, pré-validação eager, clusterização por escopo e execução na OpenAPI.
Consome o Microsserviço de Backend exclusivamente via MicroserviceApiClient (HTTP REST),
sem nenhuma query SQL ou import de submódulos do microsserviço.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Tuple, Optional
from uuid import UUID

from automacao.domain.models import SignerData, AttachmentData
from automacao.domain.exceptions import BaseFlowException, CorruptedDocumentError
from automacao.core.validator import TaskPayloadValidator
from automacao.core.clusterizer import DocumentScopeClusterizer
from automacao.core.envelope_manager import EnvelopeLifecycleManager
from automacao.domain.enums import JourneyStatus, MaintenanceReason, AutomationNode
from automacao.infrastructure.openapi_client import OpenApiV2Client
from automacao.infrastructure.microservice_client import MicroserviceApiClient


class OrchestratorController:
    """
    Controlador principal do fluxo da automação RPA.

    Orquestra as seguintes fases sequenciais:
    1. Parseamento da tarefa recebida do MongoDB / Fluid.
    2. Pré-Validação Completa Antecipada ('Tudo de uma Vez').
    3. Clusterização documental por cálculo determinístico de SHA256.
    4. Persistência de Processos e Jornadas via API REST do microsserviço.
    5. Submissão à OpenAPI v2 com suporte a upload multipart e substituição seletiva.
    """

    def __init__(
        self,
        api_client: Optional[MicroserviceApiClient] = None,
        openapi_client: Optional[OpenApiV2Client] = None
    ):
        """
        Inicializa o controlador orquestrador e seus subsistemas.

        Parâmetros:
            api_client (Optional[MicroserviceApiClient]): Cliente REST com o microsserviço.
            openapi_client (Optional[OpenApiV2Client]): Cliente HTTP de integração com a API externa.
        """
        self.api_client = api_client or MicroserviceApiClient()
        self.openapi_client = openapi_client or OpenApiV2Client()

        self.validator = TaskPayloadValidator()
        self.clusterizer = DocumentScopeClusterizer()
        self.lifecycle_manager = EnvelopeLifecycleManager(
            openapi_client=self.openapi_client,
            api_client=self.api_client
        )

    @staticmethod
    def _extract_mongo_id(task_payload: Dict[str, Any]) -> str:
        """Extrai o mongo_id suportando formatos String ou Object ($oid)."""
        raw_id = task_payload.get("_id")
        if isinstance(raw_id, dict):
            return str(raw_id.get("$oid") or raw_id)
        if raw_id:
            return str(raw_id)
        return "mongo_default_id"

    def parse_mongo_payload(self, task_payload: Dict[str, Any]) -> Tuple[List[SignerData], List[AttachmentData]]:
        """
        Extrai e estrutura os signatários e arquivos anexos a partir do payload recebido da tarefa MongoDB / Fluid.

        Realiza a leitura da matriz de assinantes mapeando os IDs de campos dos formulários Fluid (10410 ou 12905).

        Parâmetros:
            task_payload (Dict[str, Any]): Dicionário com o payload íntegro vindo da esteira.

        Retorno:
            Tuple[List[SignerData], List[AttachmentData]]: Tupla com a lista de signatários e a lista de anexos.
        """
        dispatch_info = task_payload.get("infos_envio", {})
        attributes = dispatch_info.get("atributos", {})
        raw_attachments = dispatch_info.get("anexos", [])

        # Parse de Anexos
        attachments: List[AttachmentData] = []
        for att in raw_attachments:
            file_size_raw = att.get("tamanho") if att.get("tamanho") is not None else att.get("size")
            if file_size_raw is None:
                file_size_raw = att.get("size_bytes")
            if file_size_raw is None:
                file_size_raw = att.get("byte_length")

            file_size = None
            if file_size_raw is not None:
                try:
                    file_size = int(file_size_raw)
                except (ValueError, TypeError):
                    file_size = None

            is_corrupted = bool(
                att.get("corrompido") or
                att.get("is_corrupted") or
                str(att.get("status", "")).upper() in ("ERRO", "FALHA", "CORROMPIDO", "SEM_CONTEUDO", "VAZIO") or
                str(att.get("situacao", "")).upper() in ("ERRO", "FALHA", "CORROMPIDO", "SEM_CONTEUDO", "VAZIO")
            )
            corruption_reason = att.get("motivo_corrupcao") or att.get("corruption_reason")

            attachments.append(
                AttachmentData(
                    name=att.get("nome", "").strip() or att.get("name", "anexo.pdf").strip(),
                    hash_code=att.get("hash", "").strip() or att.get("hash_sha256", "").strip(),
                    doc_type_id=att.get("tipo_doc_id") or att.get("id_tipo_documento") or att.get("doc_type_id"),
                    extension=att.get("extensao", "pdf"),
                    binary_content=att.get("conteudo_binario") or att.get("binary_content"),
                    file_size=file_size,
                    is_corrupted=is_corrupted,
                    corruption_reason=corruption_reason
                )
            )

        # Parse de Signatários (Suporta matriz Fluid 10410/12905 e lista direta de dicionários)
        raw_table = (
            attributes.get("10410") or
            attributes.get("12905") or
            dispatch_info.get("signatarios") or
            task_payload.get("signatarios") or
            []
        )
        signers: List[SignerData] = []

        if isinstance(raw_table, list):
            for idx, row in enumerate(raw_table):
                if isinstance(row, list):
                    # Formato matriz do Fluid: [{"id": 12909, "valor": "..."}, ...]
                    row_fields = {
                        item["id"]: item.get("valor", "")
                        for item in row
                        if isinstance(item, dict) and "id" in item
                    }

                    tax_id = row_fields.get(10411) or row_fields.get(12909) or attributes.get("4335") or ""
                    name = row_fields.get(10412) or row_fields.get(12910) or attributes.get("3305") or ""
                    role = row_fields.get(8665) or row_fields.get(11248) or row_fields.get(12911) or "Signatário"
                    order_str = row_fields.get(10417) or row_fields.get(12906) or "1"
                    channel_raw = row_fields.get(10414) or row_fields.get(12912) or "E-mail"
                    email = row_fields.get(10415) or row_fields.get(12913) or row_fields.get(12908) or attributes.get("11675") or ""
                    phone = row_fields.get(10416) or row_fields.get(12914) or attributes.get("12044") or ""
                    sig_type_raw = row_fields.get(10418) or row_fields.get(12915) or "Eletrônica"

                    docs_raw = row_fields.get(10751) or row_fields.get(11249) or row_fields.get(12857) or "[]"

                    doc_ids = []
                    if isinstance(docs_raw, list):
                        doc_ids = [str(d) for d in docs_raw]
                    elif isinstance(docs_raw, str):
                        try:
                            parsed_list = json.loads(docs_raw)
                            doc_ids = [str(d) for d in parsed_list]
                        except Exception:
                            doc_ids = [docs_raw]

                    validation_channel = "WHATSAPP" if "WHATSAPP" in str(channel_raw).upper() else "EMAIL"
                    signature_type = "DIGITAL" if "DIGITAL" in str(sig_type_raw).upper() or "CERTIFICADO" in str(sig_type_raw).upper() else "ELETRONIC"

                    try:
                        order = int(order_str)
                    except ValueError:
                        order = 1

                    signers.append(
                        SignerData(
                            tax_id=str(tax_id).strip(),
                            name=str(name).strip(),
                            order=order,
                            role=str(role).strip(),
                            email=str(email).strip(),
                            phone=str(phone).strip(),
                            signature_type=signature_type,
                            validation_channel=validation_channel,
                            document_ids=doc_ids
                        )
                    )
                elif isinstance(row, dict):
                    # Formato direto de dicionário
                    tax_id = row.get("cpf") or row.get("tax_id") or row.get("cnpj") or ""
                    name = row.get("nome") or row.get("name") or ""
                    role = row.get("papel") or row.get("role") or "ASSINAR"
                    order = int(row.get("ordem") or row.get("order") or (idx + 1))
                    email = row.get("email") or ""
                    phone = row.get("telefone") or row.get("phone") or ""
                    signature_type = row.get("tipo_assinatura") or row.get("signature_type") or "ELETRONIC"
                    validation_channel = row.get("canal_validacao") or row.get("validation_channel") or "WHATSAPP"
                    raw_docs = row.get("documentos") or row.get("document_ids") or []

                    doc_ids = [str(d).strip() for d in raw_docs if d is not None]
                    if not doc_ids:
                        doc_ids = [str(att.doc_type_id) for att in attachments if att.doc_type_id is not None]

                    signers.append(
                        SignerData(
                            tax_id=str(tax_id).strip(),
                            name=str(name).strip(),
                            order=order,
                            role=str(role).strip(),
                            email=str(email).strip(),
                            phone=str(phone).strip(),
                            signature_type=signature_type,
                            validation_channel=validation_channel,
                            document_ids=doc_ids
                        )
                    )

        return signers, attachments

    def execute_workflow(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ponto de entrada do orquestrador RPA com roteamento dinâmico por Nodos (12 a 16).

        Nodos suportados:
            12: CRIAR_ENVELOPE (padrão) - Validação, clusterização e criação inicial.
            13: ATUALIZAR_METODO_ASSINATURA - Troca de método via PUT (Presencial, WhatsApp, E-mail).
            14: TROCAR_ASSINANTES - Substituição seletiva por novos signatários.
            15: TROCAR_DOCUMENTO - Substituição seletiva por novos documentos.
            16: CANCELAR_ENVELOPE - Cancelamento do envelope ativo na OpenAPI e banco.

        Parâmetros:
            task_payload (Dict[str, Any]): Dados recebidos da esteira Fluid / MongoDB.

        Retorno:
            Dict[str, Any]: Resumo da execução contendo status, nodo, ID da jornada e envelopes.
        """
        nodo_raw = task_payload.get("nodo") or task_payload.get("id_nodo") or AutomationNode.CREATE_ENVELOPE.value
        try:
            nodo = AutomationNode(int(nodo_raw))
        except (ValueError, TypeError):
            nodo = AutomationNode.CREATE_ENVELOPE

        if nodo == AutomationNode.UPDATE_SIGNATURE_METHOD:
            return self._handle_update_signature_method(task_payload)
        elif nodo == AutomationNode.CHANGE_SIGNERS:
            return self._handle_cluster_workflow(task_payload, nodo=AutomationNode.CHANGE_SIGNERS, event_type="SIGNERS_CHANGED")
        elif nodo == AutomationNode.CHANGE_DOCUMENTS:
            return self._handle_cluster_workflow(task_payload, nodo=AutomationNode.CHANGE_DOCUMENTS, event_type="DOCUMENTS_CHANGED")
        elif nodo == AutomationNode.CANCEL_ENVELOPE:
            return self._handle_cancel_envelope(task_payload)
        else:
            return self._handle_create_envelope(task_payload)

    def _handle_create_envelope(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o fluxo padrão de criação de envelope (Nodo 12)."""
        return self._handle_cluster_workflow(
            task_payload,
            nodo=AutomationNode.CREATE_ENVELOPE,
            event_type="ENVELOPE_PROCESSED"
        )

    def _handle_cluster_workflow(
        self,
        task_payload: Dict[str, Any],
        nodo: AutomationNode,
        event_type: str = "ENVELOPE_PROCESSED"
    ) -> Dict[str, Any]:
        """Processa fluxos baseados em clusterização (Nodos 12, 14 e 15)."""
        mongo_id = self._extract_mongo_id(task_payload)
        process_number = task_payload.get("num_processo", 0)
        process_name = task_payload.get("nome_processo", "Processo Genérico")
        initial_id = task_payload.get("id_inicial")

        # 1. Parseamento
        signers, attachments = self.parse_mongo_payload(task_payload)

        # 2. Pré-Validação Completa ("Tudo de uma Vez")
        try:
            self.validator.validate_task_data(signers, attachments)
        except BaseFlowException as err:
            # Registra jornada com status de falha/intervenção via API do microsserviço
            journey = self.api_client.get_or_create_journey(
                mongo_id=mongo_id,
                process_name=process_name,
                process_number=process_number,
                fluid_payload=task_payload,
                initial_id=initial_id
            )
            self.api_client.update_journey_status(
                journey_id=journey["id"],
                status=JourneyStatus.FAILED,
                details="; ".join(err.errors)
            )

            reason_code = (
                MaintenanceReason.CORRUPTED_DOCUMENT
                if isinstance(err, CorruptedDocumentError)
                else MaintenanceReason.INVALID_SIGNER_DATA
            )
            try:
                self.api_client.cancel_envelope_maintenance(
                    envelope_id=journey["id"],
                    reason_code=reason_code,
                    detailed_description="; ".join(err.errors),
                    canceled_by="RPA_VALIDATOR"
                )
            except Exception:
                pass
            raise

        # 3. Clusterização por Escopo Documental
        clusters = self.clusterizer.clusterize(signers, attachments)

        # 4. Persistência de Processo e Jornada via API REST
        journey = self.api_client.get_or_create_journey(
            mongo_id=mongo_id,
            process_name=process_name,
            process_number=process_number,
            fluid_payload=task_payload,
            initial_id=initial_id
        )

        # 5. Submissão dos Clusters à OpenAPI v2
        envelopes_processed = []
        for cluster in clusters:
            env_res = self.lifecycle_manager.process_cluster(
                request_id=UUID(journey["id"]),
                process_number=process_number,
                cluster=cluster
            )
            envelopes_processed.append(env_res)

        # 6. Atualiza jornada para SUCCESS
        self.api_client.update_journey_status(
            journey_id=journey["id"],
            status=JourneyStatus.COMPLETED,
            details=f"Processados {len(envelopes_processed)} envelopes com sucesso."
        )

        return {
            "status": "SUCESSO",
            "nodo": nodo.value,
            "journey_id": str(journey["id"]),
            "process_number": process_number,
            "clusters_count": len(clusters),
            "envelopes": envelopes_processed
        }

    def _handle_update_signature_method(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executa a alteração de canal/método de assinatura via PUT (Nodo 13)."""
        mongo_id = self._extract_mongo_id(task_payload)
        process_number = task_payload.get("num_processo", 0)
        process_name = task_payload.get("nome_processo", "Processo Genérico")
        initial_id = task_payload.get("id_inicial")

        signers, _ = self.parse_mongo_payload(task_payload)

        journey = self.api_client.get_or_create_journey(
            mongo_id=mongo_id,
            process_name=process_name,
            process_number=process_number,
            fluid_payload=task_payload,
            initial_id=initial_id
        )

        result = self.lifecycle_manager.update_signature_method(
            request_id=UUID(journey["id"]),
            process_number=process_number,
            signers=signers
        )

        return {
            "status": "SUCESSO",
            "nodo": AutomationNode.UPDATE_SIGNATURE_METHOD.value,
            "journey_id": str(journey["id"]),
            "process_number": process_number,
            **result
        }

    def _handle_cancel_envelope(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Executa o cancelamento explícito do envelope na API externa e no microsserviço (Nodo 16)."""
        mongo_id = self._extract_mongo_id(task_payload)
        process_number = task_payload.get("num_processo", 0)
        process_name = task_payload.get("nome_processo", "Processo Genérico")
        initial_id = task_payload.get("id_inicial")
        motivo = task_payload.get("motivo_cancelamento", "Cancelamento solicitado via esteira Fluid")

        journey = self.api_client.get_or_create_journey(
            mongo_id=mongo_id,
            process_name=process_name,
            process_number=process_number,
            fluid_payload=task_payload,
            initial_id=initial_id
        )

        result = self.lifecycle_manager.cancel_active_envelope(
            request_id=UUID(journey["id"]),
            process_number=process_number,
            reason=motivo
        )

        return {
            "status": "SUCESSO",
            "nodo": AutomationNode.CANCEL_ENVELOPE.value,
            "journey_id": str(journey["id"]),
            "process_number": process_number,
            **result
        }
