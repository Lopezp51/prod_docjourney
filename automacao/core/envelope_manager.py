"""
Módulo de Gestão de Ciclo de Vida e Substituição Seletiva de Envelopes.
Executa a criação de envelopes no banco, comunicação com a OpenAPI v2, upload de binários multipart
e substituição seletiva (cancelamento com versionamento incremental da versão anterior).
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from typing import Dict, Any, Optional
from uuid import UUID

from automacao.domain.models import EnvelopeCluster, DocumentTypeMapping, DocumentTypeItem
from automacao.infrastructure.openapi_client import OpenApiV2Client
from microservico.infrastructure.repositories import (
    EnvelopeRepository,
    AssociateRepository,
    DocumentRepository,
    EnvelopeSignerRepository
)
from microservico.domain.enums import (
    EnvelopeStatus,
    ProviderType,
    SignatureType,
    ValidationChannel
)


class EnvelopeLifecycleManager:
    """
    Gerenciador de Ciclo de Vida e Substituição de Envelopes.

    Responsável por:
    1. Detectar envelopes pré-existentes na mesma jornada para aplicar substituição seletiva
       (marca o envelope anterior como REPLACED_CANCELED e incrementa a versão).
    2. Persistir o novo envelope no banco relacional.
    3. Construir o payload de participantes e disparar o POST /v2/envelope/create na OpenAPI.
    4. Realizar o upload multipart dos binários dos documentos associados ao envelope.
    5. Persistir vínculos relacionais nas tabelas 'documents' e 'envelope_signers'.
    """

    def __init__(
        self,
        openapi_client: OpenApiV2Client,
        envelope_repo: EnvelopeRepository,
        associate_repo: AssociateRepository,
        document_repo: Optional[DocumentRepository] = None,
        signer_repo: Optional[EnvelopeSignerRepository] = None
    ):
        """
        Inicializa o gerenciador de ciclo de vida.

        Parâmetros:
            openapi_client (OpenApiV2Client): Cliente de integração com a OpenAPI v2.
            envelope_repo (EnvelopeRepository): Repositório para persistência de envelopes.
            associate_repo (AssociateRepository): Repositório de cadastro único de associados.
            document_repo (Optional[DocumentRepository]): Repositório para documentos de envelopes.
            signer_repo (Optional[EnvelopeSignerRepository]): Repositório para vínculos de signatários.
        """
        self.openapi_client = openapi_client
        self.envelope_repo = envelope_repo
        self.associate_repo = associate_repo
        self.document_repo = document_repo
        self.signer_repo = signer_repo

    def process_cluster(
        self,
        request_id: UUID,
        process_number: int,
        cluster: EnvelopeCluster,
        provider: str = "CERTISIGN"
    ) -> Dict[str, Any]:
        """
        Processa um cluster documental: executa substituição de versões anteriores, cria o envelope e envia arquivos.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai (journey_requests.id).
            process_number (int): Número do processo no Fluid / cooperativa.
            cluster (EnvelopeCluster): Grupo contendo hash de escopo, documentos, signatários e anexos.
            provider (str): Nome do provedor de assinatura ('CERTISIGN' ou 'ADESAO').

        Retorno:
            Dict[str, Any]: Resumo da operação contendo IDs do banco e da OpenAPI, versão e contadores.
        """
        # 1. Verifica envelopes ativos para substituição seletiva e versionamento
        existing_envs = self.envelope_repo.list_active_by_request(request_id)
        max_version = self.envelope_repo.get_max_version_by_request(request_id)
        version = max_version + 1 if max_version > 0 else 1

        if existing_envs:
            for old_env in existing_envs:
                if old_env.external_envelope_id:
                    self.openapi_client.delete_envelope(old_env.external_envelope_id)
                self.envelope_repo.mark_replaced_cancelled(old_env.id)

        # 2. Registra o envelope no banco de dados
        provider_type = ProviderType.ADESAO if provider.upper() == "ADESAO" else ProviderType.CERTISIGN
        db_envelope = self.envelope_repo.create_envelope(
            request_id=request_id,
            document_scope_hash=cluster.scope_hash,
            provider=provider_type,
            envelope_version=version
        )

        # 3. Monta o payload de signatários para a OpenAPI e persiste signatários
        signers_payload = []
        first_assoc_id = None

        for sig in cluster.signers:
            # Garante que o associado está cadastrado ou atualizado
            assoc = self.associate_repo.upsert(
                tax_id=sig.tax_id,
                name=sig.name,
                email=sig.email,
                phone=sig.phone
            )
            if first_assoc_id is None:
                first_assoc_id = assoc.id

            # Persiste o vínculo do signatário com o envelope
            if self.signer_repo:
                sig_type = (
                    SignatureType.DIGITAL
                    if "DIGITAL" in str(sig.signature_type).upper()
                    else SignatureType.ELECTRONIC
                )
                val_channel = (
                    ValidationChannel.WHATSAPP
                    if "WHATSAPP" in str(sig.validation_channel).upper()
                    else ValidationChannel.EMAIL
                )
                self.signer_repo.add_signer(
                    envelope_id=db_envelope.id,
                    associate_id=assoc.id,
                    signer_role=sig.role,
                    signature_order=sig.order,
                    signature_type=sig_type,
                    validation_channel=val_channel
                )

            signer_dict = {
                "cpf": sig.tax_id,
                "name": sig.name,
                "email": sig.email or "",
                "phone": sig.phone or "",
                "ddi": 55,
                "title": [sig.role],
                "flowRole": "ASSINAR",
                "signatureType": sig.signature_type.upper(),
                "secondAuthFactor": True if sig.validation_channel.upper() == "WHATSAPP" else False,
                "authenticationMethods": [{"method": sig.validation_channel.upper()}] if sig.validation_channel else []
            }
            signers_payload.append(signer_dict)

        create_payload = {
            "coop": "0703",
            "agency": "11",
            "account": "1111111111",
            "title": f"Processo #{process_number} - Cluster {cluster.scope_hash[:8]}",
            "comment": f"Envio de Documentos da Solicitação #{process_number}",
            "tags": [f"PROCESSO_{process_number}"],
            "provider": provider.upper(),
            "notificationEmails": ["notificacao@sicredi.com.br"],
            "allowSignatureOrder": False,
            "documentSignaturePattern": "PADES",
            "hasValueElectronicChannel": False,
            "signers": signers_payload
        }

        # 4. Executa a criação na OpenAPI
        response_create = self.openapi_client.create_envelope(create_payload)
        external_envelope_id = response_create.get("id")

        # Atualiza a referência no banco relacional
        self.envelope_repo.update_external_id(
            envelope_id=db_envelope.id,
            external_envelope_id=external_envelope_id,
            status=EnvelopeStatus.PENDING_SIGNATURE
        )

        # 5. Upload Binário Multipart dos Documentos (POST /files/envelope/:id/files) e persistência
        files_data = []
        doc_type_mappings = []

        for att in cluster.attachments:
            bin_data = att.binary_content or b"%PDF-1.4 Mock PDF Content"
            files_data.append((att.name, bin_data, "application/pdf"))

            doc_type_code = f"DOCUMENT_TYPE_TTD_{att.doc_type_id or 656}"
            doc_type_mappings.append(
                DocumentTypeMapping(
                    file_name=att.name,
                    document_types=[DocumentTypeItem(document_type=doc_type_code, is_attachment=False)]
                )
            )

            # Persiste documento no banco
            if self.document_repo and first_assoc_id:
                self.document_repo.add_document(
                    envelope_id=db_envelope.id,
                    associate_id=first_assoc_id,
                    file_name=att.name,
                    source_hash=att.hash_code,
                    document_type_id=att.doc_type_id,
                    extension=att.extension
                )

        if files_data:
            self.openapi_client.upload_envelope_files(
                envelope_id=external_envelope_id,
                files_data=files_data,
                document_types_mapping=doc_type_mappings
            )

        return {
            "envelope_db_id": str(db_envelope.id),
            "external_envelope_id": external_envelope_id,
            "scope_hash": cluster.scope_hash,
            "version": version,
            "signers_count": len(cluster.signers),
            "attachments_count": len(cluster.attachments)
        }
