"""
Módulo do Controlador Orquestrador da Automação RPA.
Coordena a extração do payload do MongoDB, pré-validação eager, clusterização por escopo e execução na OpenAPI.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Tuple

from automacao.domain.models import SignerData, AttachmentData
from automacao.domain.exceptions import BaseFlowException, CorruptedDocumentError
from automacao.core.validator import TaskPayloadValidator
from automacao.core.clusterizer import DocumentScopeClusterizer
from automacao.core.envelope_manager import EnvelopeLifecycleManager

from microservico.domain.enums import JourneyStatus, MaintenanceReason
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.repositories import (
    ProcessRepository,
    JourneyRepository,
    EnvelopeRepository,
    AssociateRepository,
    DocumentRepository,
    EnvelopeSignerRepository,
    MaintenanceHistoryRepository
)
from microservico.notifier.rabbitmq_client import RabbitMQClient
from automacao.infrastructure.openapi_client import OpenApiV2Client


class OrchestratorController:
    """
    Controlador principal do fluxo da automação RPA.

    Orquestra as seguintes fases sequenciais:
    1. Parseamento da tarefa recebida do MongoDB / Fluid.
    2. Pré-Validação Completa Antecipada ('Tudo de uma Vez').
    3. Clusterização documental por cálculo determinístico de SHA256.
    4. Persistência de Processos e Jornadas no banco relacional.
    5. Submissão à OpenAPI v2 com suporte a upload multipart e substituição seletiva.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        openapi_client: OpenApiV2Client = None,
        rabbitmq_client: RabbitMQClient = None
    ):
        """
        Inicializa o controlador orquestrador e seus subsistemas.

        Parâmetros:
            db_manager (DatabaseManager): Gerenciador de conexão com o banco relacional.
            openapi_client (OpenApiV2Client): Cliente HTTP de integração com a API externa.
            rabbitmq_client (RabbitMQClient): Cliente para mensageria e eventos no RabbitMQ.
        """
        self.db_manager = db_manager
        self.openapi_client = openapi_client or OpenApiV2Client()

        self.process_repo = ProcessRepository(db_manager)
        self.journey_repo = JourneyRepository(db_manager)
        self.envelope_repo = EnvelopeRepository(db_manager)
        self.associate_repo = AssociateRepository(db_manager)
        self.document_repo = DocumentRepository(db_manager)
        self.signer_repo = EnvelopeSignerRepository(db_manager)
        self.maintenance_repo = MaintenanceHistoryRepository(db_manager)

        self.validator = TaskPayloadValidator()
        self.clusterizer = DocumentScopeClusterizer()
        self.lifecycle_manager = EnvelopeLifecycleManager(
            openapi_client=self.openapi_client,
            envelope_repo=self.envelope_repo,
            associate_repo=self.associate_repo,
            document_repo=self.document_repo,
            signer_repo=self.signer_repo
        )
        self.rabbitmq_client = rabbitmq_client or RabbitMQClient(queue_name="docjourney_status_queue")

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
            # Extração segura de tamanho de arquivo (se informado, preservando 0 como valor válido)
            file_size_raw = att.get("tamanho")
            if file_size_raw is None:
                file_size_raw = att.get("size")
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
                    name=att.get("nome", "").strip(),
                    hash_code=att.get("hash", "").strip(),
                    doc_type_id=att.get("tipo_doc_id"),
                    extension=att.get("extensao", "pdf"),
                    binary_content=att.get("conteudo_binario") or att.get("binary_content"),
                    file_size=file_size,
                    is_corrupted=is_corrupted,
                    corruption_reason=corruption_reason
                )
            )

        # Parse da Tabela de Assinantes (Campos de formulário Fluid: 10410 ou 12905)
        raw_table = attributes.get("10410") or attributes.get("12905") or []
        signers: List[SignerData] = []

        if isinstance(raw_table, list):
            for row in raw_table:
                if isinstance(row, list):
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

                    # Parse seguro de documentos vinculados ao participante
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

        return signers, attachments

    def execute_workflow(self, task_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executa o fluxo íntegro e orquestrado da automação para a tarefa informada.

        Passos:
        1. Parseamento dos signatários e anexos.
        2. Pré-validação com acúmulo de pendências em BulkValidationError.
        3. Agrupamento em clusters de envelopes por escopo documental.
        4. Criação da jornada idempotente no banco relacional.
        5. Disparo das criações e uploads multipart na OpenAPI v2.

        Parâmetros:
            task_payload (Dict[str, Any]): Dados recebidos da tarefa do processo.

        Retorno:
            Dict[str, Any]: Resumo da execução contendo status, ID da jornada e envelopes criados.
        """
        mongo_id = str(task_payload.get("_id", {}).get("$oid") or task_payload.get("_id") or "mongo_default_id")
        process_number = task_payload.get("num_processo", 0)
        process_name = task_payload.get("nome_processo", "Processo Genérico")
        initial_id = task_payload.get("id_inicial")

        # 1. Parseamento
        signers, attachments = self.parse_mongo_payload(task_payload)

        # 2. Pré-Validação Completa ("Tudo de uma Vez")
        try:
            self.validator.validate_task_data(signers, attachments)
        except BaseFlowException as err:
            # Garante que a jornada seja persistida no banco com status FAILED
            # e a ocorrência impeditiva seja registrada para auditoria em maintenance_history
            process = self.process_repo.get_or_create(name=process_name)
            journey = self.journey_repo.create_journey(
                process_id=process.id,
                mongo_id=mongo_id,
                process_number=process_number,
                fluid_payload=task_payload,
                initial_id=initial_id
            )
            self.journey_repo.update_status(journey.id, JourneyStatus.FAILED)

            reason_code = (
                MaintenanceReason.CORRUPTED_DOCUMENT
                if isinstance(err, CorruptedDocumentError)
                else MaintenanceReason.INVALID_SIGNER_DATA
            )
            self.maintenance_repo.log_maintenance(
                request_id=journey.id,
                reason_code=reason_code,
                detailed_description="; ".join(err.errors)
            )

            # Notifica falha na fila RabbitMQ
            self.rabbitmq_client.publish_message({
                "event_type": "VALIDATION_FAILED",
                "process_number": process_number,
                "process_name": process_name,
                "journey_id": str(journey.id),
                "reason_code": reason_code.value,
                "errors": err.errors,
                "timestamp": datetime.now().isoformat()
            })
            raise

        # 3. Clusterização por Escopo Documental
        clusters = self.clusterizer.clusterize(signers, attachments)

        # 4. Persistência de Processo e Jornada no Banco
        process = self.process_repo.get_or_create(name=process_name)
        journey = self.journey_repo.create_journey(
            process_id=process.id,
            mongo_id=mongo_id,
            process_number=process_number,
            fluid_payload=task_payload,
            initial_id=initial_id
        )

        # 5. Submissão dos Clusters à OpenAPI v2
        envelopes_processed = []
        for cluster in clusters:
            env_res = self.lifecycle_manager.process_cluster(
                request_id=journey.id,
                process_number=process_number,
                cluster=cluster
            )
            envelopes_processed.append(env_res)

            # 6. Notifica o RabbitMQ para cada envelope criado/substituído
            self.rabbitmq_client.publish_message({
                "event_type": "ENVELOPE_PROCESSED",
                "process_number": process_number,
                "process_name": process_name,
                "journey_id": str(journey.id),
                "envelope_id": str(env_res.get("envelope_id")),
                "external_envelope_id": env_res.get("external_envelope_id"),
                "status": str(env_res.get("status")),
                "version": env_res.get("version"),
                "documents_count": len(cluster.document_ids),
                "signers_count": len(cluster.signers),
                "timestamp": datetime.now().isoformat()
            })

        return {
            "status": "SUCESSO",
            "journey_id": str(journey.id),
            "process_number": process_number,
            "clusters_count": len(clusters),
            "envelopes": envelopes_processed
        }
