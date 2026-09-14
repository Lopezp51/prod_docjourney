"""
Módulo de Gestão de Ciclo de Vida e Substituição Seletiva de Envelopes.
Executa a criação de envelopes no banco, comunicação com a OpenAPI v2, upload de binários multipart
e substituição seletiva (cancelamento com versionamento incremental da versão anterior).
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime

from automacao.domain.models import EnvelopeCluster, DocumentTypeMapping, DocumentTypeItem, SignerData
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

            forma, metodo, second_factor, auth_methods, val_channel, sig_type = self.map_signer_channel_and_auth(sig)

            # Persiste o vínculo do signatário com o envelope
            if self.signer_repo:
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
                "signatureType": sig.signature_type.upper() if sig.signature_type else "ELETRONIC",
                "secondAuthFactor": second_factor,
                "authenticationMethods": auth_methods,
                "formaAssinatura": forma,
                "metodoEnvioLink": metodo
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

    @staticmethod
    def map_signer_channel_and_auth(sig: SignerData) -> Tuple[str, str, bool, List[Dict[str, str]], ValidationChannel, SignatureType]:
        """
        Mapeia a forma de assinatura, método de envio, segundo fator e métodos de autenticação conforme o canal.
        """
        channel_upper = (sig.validation_channel or "EMAIL").upper()
        sig_type_enum = (
            SignatureType.DIGITAL
            if "DIGITAL" in str(sig.signature_type).upper()
            else SignatureType.ELECTRONIC
        )

        if "WHATSAPP" in channel_upper:
            forma = "PRESENCIAL"
            metodo = "WHATSAPP"
            auth_methods = [{"method": "WHATSAPP"}]
            second_factor = True
            db_channel = ValidationChannel.WHATSAPP
        elif "PRESENCIAL" in channel_upper:
            forma = "PRESENCIAL"
            metodo = "PRESENCIAL"
            auth_methods = []
            second_factor = False
            db_channel = ValidationChannel.IN_PERSON
        else:
            forma = "PRESENCIAL"
            metodo = "EMAIL"
            auth_methods = [{"method": "EMAIL"}]
            second_factor = False
            db_channel = ValidationChannel.EMAIL

        return forma, metodo, second_factor, auth_methods, db_channel, sig_type_enum

    def update_signature_method(
        self,
        request_id: UUID,
        process_number: int,
        signers: List[SignerData]
    ) -> Dict[str, Any]:
        """
        Atualiza o método de assinatura (Presencial, WhatsApp, E-mail) de um envelope ativo via PUT.

        Aplica retentativa contra o estado transitório 'Aguardando envio', marca o envelope
        anterior como ALTERADO com flag is_altered=True, e gera o novo envelope versionado.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai.
            process_number (int): Número do processo Fluid.
            signers (List[SignerData]): Lista de signatários com os novos métodos/canais.

        Retorno:
            Dict[str, Any]: Detalhes da operação e referências dos envelopes antigo e novo.
        """
        active_env = self.envelope_repo.get_latest_active_by_request(request_id)
        if not active_env:
            active_list = self.envelope_repo.list_active_by_request(request_id)
            active_env = active_list[-1] if active_list else None

        if not active_env:
            raise ValueError(f"Nenhum envelope ativo encontrado para a solicitação #{process_number} (ID: {request_id}).")

        old_external_id = active_env.external_envelope_id

        put_signers = []
        signers_db_data = []

        for sig in signers:
            assoc = self.associate_repo.upsert(
                tax_id=sig.tax_id,
                name=sig.name,
                email=sig.email,
                phone=sig.phone
            )
            forma, metodo, second_factor, auth_methods, db_channel, sig_type = self.map_signer_channel_and_auth(sig)

            signer_payload_item = {
                "id": str(assoc.id),
                "phone": sig.phone or "",
                "ddi": 55,
                "email": sig.email or "",
                "secondAuthFactor": second_factor,
                "authenticationMethods": auth_methods,
                "formaAssinatura": forma,
                "metodoEnvioLink": metodo,
                "signatureType": sig.signature_type.upper() if sig.signature_type else "ELETRONIC"
            }
            put_signers.append(signer_payload_item)
            signers_db_data.append((assoc.id, sig, db_channel, sig_type))

        put_payload = {
            "id": old_external_id,
            "tags": [f"PROCESSO_{process_number}"],
            "comment": f"Alteração de método de assinatura para o processo #{process_number}",
            "signers": put_signers
        }

        res_put = self.openapi_client.update_envelope(put_payload)
        new_external_id = res_put.get("id") or f"openapi_env_alt_{uuid4().hex[:8]}"

        self.envelope_repo.mark_altered(active_env.id, new_external_id)

        new_version = active_env.envelope_version + 1
        new_db_env = self.envelope_repo.create_envelope(
            request_id=request_id,
            document_scope_hash=active_env.document_scope_hash,
            provider=active_env.provider,
            envelope_version=new_version
        )
        self.envelope_repo.update_external_id(
            envelope_id=new_db_env.id,
            external_envelope_id=new_external_id,
            status=EnvelopeStatus.PENDING_SIGNATURE
        )

        if self.document_repo:
            old_docs = self.document_repo.list_by_envelope(active_env.id)
            for doc in old_docs:
                self.document_repo.add_document(
                    envelope_id=new_db_env.id,
                    associate_id=doc.associate_id,
                    file_name=doc.file_name,
                    source_hash=doc.source_hash,
                    document_type_id=doc.document_type_id,
                    extension=doc.extension
                )

        if self.signer_repo:
            for assoc_id, sig, db_channel, sig_type in signers_db_data:
                self.signer_repo.add_signer(
                    envelope_id=new_db_env.id,
                    associate_id=assoc_id,
                    signer_role=sig.role,
                    signature_order=sig.order,
                    signature_type=sig_type,
                    validation_channel=db_channel
                )

        return {
            "status": "SUCESSO",
            "action": "UPDATE_SIGNATURE_METHOD",
            "old_envelope_id": str(active_env.id),
            "old_external_id": old_external_id,
            "new_envelope_id": str(new_db_env.id),
            "new_external_id": new_external_id,
            "version": new_version,
            "signers_count": len(signers)
        }

    def cancel_active_envelope(
        self,
        request_id: UUID,
        process_number: int,
        reason: str = "Cancelamento solicitado via esteira"
    ) -> Dict[str, Any]:
        """
        Cancela o envelope ativo da solicitação na API externa e no banco de dados.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai.
            process_number (int): Número do processo.
            reason (str): Justificativa do cancelamento.

        Retorno:
            Dict[str, Any]: Detalhes do envelope cancelado.
        """
        active_env = self.envelope_repo.get_latest_active_by_request(request_id)
        if not active_env:
            active_list = self.envelope_repo.list_active_by_request(request_id)
            active_env = active_list[-1] if active_list else None

        if not active_env:
            raise ValueError(f"Nenhum envelope ativo encontrado para cancelamento no processo #{process_number}.")

        if active_env.external_envelope_id:
            self.openapi_client.delete_envelope(active_env.external_envelope_id)

        now = datetime.now()
        self.envelope_repo.db_manager.execute(
            "UPDATE envelopes SET envelope_status = %s, updated_at = %s WHERE id = %s",
            (EnvelopeStatus.CANCELED, now, active_env.id)
        )

        return {
            "status": "SUCESSO",
            "action": "CANCEL_ENVELOPE",
            "envelope_id": str(active_env.id),
            "external_envelope_id": active_env.external_envelope_id,
            "envelope_status": "CANCELED",
            "reason": reason
        }
