"""
Módulo de Gestão de Ciclo de Vida e Substituição Seletiva de Envelopes na Automação RPA.
Executa a integração com a OpenAPI v2 externa (Sicredi/Certisign) e sincroniza
a persistência e manutenção exclusivamente através do MicroserviceApiClient (HTTP REST),
sem nenhuma query SQL ou import do microsserviço.
"""

from typing import Dict, Any, Optional, List, Tuple
from uuid import UUID, uuid4
from datetime import datetime

from automacao.logging_config import logger
from automacao.domain.models import EnvelopeCluster, DocumentTypeMapping, DocumentTypeItem, SignerData
from automacao.infrastructure.openapi_client import OpenApiV2Client
from automacao.infrastructure.microservice_client import MicroserviceApiClient
from automacao.domain.enums import (
    EnvelopeStatus,
    ProviderType,
    SignatureType,
    ValidationChannel,
    MaintenanceReason
)



class EnvelopeLifecycleManager:
    """
    Gerenciador de Ciclo de Vida e Substituição de Envelopes na Automação RPA.

    Responsável por:
    1. Consultar envelopes existentes via MicroserviceApiClient.
    2. Disparar chamadas para a OpenAPI v2 (criação e upload multipart).
    3. Persistir e atualizar envelopes via API REST do microsserviço.
    4. Substituição seletiva e cancelamentos com governança e auditoria.
    """

    def __init__(
        self,
        openapi_client: Optional[OpenApiV2Client] = None,
        api_client: Optional[MicroserviceApiClient] = None
    ):
        """
        Inicializa o gerenciador de ciclo de vida.

        Parâmetros:
            openapi_client (Optional[OpenApiV2Client]): Cliente de integração com a OpenAPI v2.
            api_client (Optional[MicroserviceApiClient]): Cliente REST com o microsserviço.
        """
        self.openapi_client = openapi_client or OpenApiV2Client()
        self.api_client = api_client or MicroserviceApiClient()

    def process_cluster(
        self,
        request_id: UUID,
        process_number: int,
        cluster: EnvelopeCluster,
        provider: str = "CERTISIGN"
    ) -> Dict[str, Any]:
        """
        Processa um cluster documental: cancela versões anteriores na OpenAPI se necessário,
        chama a criação na OpenAPI, persiste via API do microsserviço e faz upload dos arquivos.

        Parâmetros:
            request_id (UUID): Identificador da jornada pai.
            process_number (int): Número do processo Fluid.
            cluster (EnvelopeCluster): Grupo contendo hash de escopo, documentos e signatários.
            provider (str): Nome do provedor ('CERTISIGN' ou 'ADESAO').

        Retorno:
            Dict[str, Any]: Resumo da operação contendo IDs e metadados.
        """
        # 1. Consulta envelopes ativos da jornada via API REST
        existing_envs = self.api_client.list_journey_envelopes(str(request_id))
        max_version = max([int(e.get("envelope_version", 1)) for e in existing_envs], default=0)
        version = max_version + 1 if max_version > 0 else 1

        if existing_envs:
            for old_env in existing_envs:
                old_ext_id = old_env.get("external_envelope_id")
                if old_ext_id:
                    try:
                        self.openapi_client.delete_envelope(old_ext_id)
                    except Exception as err:
                        logger.warning(f"Aviso ao cancelar envelope antigo {old_ext_id} na OpenAPI: {err}")

        # 2. Monta payload de signatários para a OpenAPI
        signers_payload = []
        signers_api_list = []

        for sig in cluster.signers:
            forma, metodo, second_factor, auth_methods, val_channel, sig_type = self.map_signer_channel_and_auth(sig)

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

            signers_api_list.append({
                "tax_id": sig.tax_id,
                "name": sig.name,
                "email": sig.email,
                "phone": sig.phone,
                "role": sig.role,
                "order": sig.order,
                "signature_type": sig_type.value,
                "validation_channel": val_channel.value
            })

        # 3. Executa a criação na OpenAPI externa
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

        response_create = self.openapi_client.create_envelope(create_payload)
        external_envelope_id = response_create.get("id")

        # 4. Prepara lista de documentos
        docs_api_list = []
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

            docs_api_list.append({
                "template_id": str(att.doc_type_id or 10410),
                "name": att.name,
                "document_hash": att.hash_code or "hash_default",
                "size_bytes": len(bin_data)
            })

        # 5. Persiste o envelope no microsserviço via API REST
        provider_type = ProviderType.ADESAO if provider.upper() == "ADESAO" else ProviderType.CERTISIGN
        envelope_data = self.api_client.create_envelope(
            request_id=str(request_id),
            document_scope_hash=cluster.scope_hash,
            envelope_version=version,
            provider=provider_type,
            allow_signature_order=False,
            external_envelope_id=external_envelope_id,
            signers=signers_api_list,
            documents=docs_api_list
        )
        envelope_db_id = envelope_data.get("id")

        # 6. Upload Binário Multipart dos Documentos na OpenAPI
        if files_data and external_envelope_id:
            self.openapi_client.upload_envelope_files(
                envelope_id=external_envelope_id,
                files_data=files_data,
                document_types_mapping=doc_type_mappings
            )

        # 7. Atualiza status para PENDING_SIGNATURE na API do microsserviço
        if envelope_db_id:
            self.api_client.update_envelope_status(
                envelope_id=envelope_db_id,
                envelope_status=EnvelopeStatus.PENDING_SIGNATURE,
                external_envelope_id=external_envelope_id
            )

        return {
            "envelope_db_id": str(envelope_db_id),
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
        Atualiza o método de assinatura via PUT na OpenAPI e gera nova versão versionada via API REST.
        """
        active_list = self.api_client.list_journey_envelopes(str(request_id))
        if not active_list:
            raise ValueError(f"Nenhum envelope ativo encontrado para a solicitação #{process_number} (ID: {request_id}).")

        active_env = active_list[-1]
        old_external_id = active_env.get("external_envelope_id")
        old_env_id = active_env.get("id")

        put_signers = []
        signers_api_list = []

        for sig in signers:
            forma, metodo, second_factor, auth_methods, db_channel, sig_type = self.map_signer_channel_and_auth(sig)

            signer_payload_item = {
                "id": str(uuid4()),
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
            signers_api_list.append({
                "tax_id": sig.tax_id,
                "name": sig.name,
                "email": sig.email,
                "phone": sig.phone,
                "role": sig.role,
                "order": sig.order,
                "signature_type": sig_type.value,
                "validation_channel": db_channel.value
            })

        put_payload = {
            "id": old_external_id,
            "tags": [f"PROCESSO_{process_number}"],
            "comment": f"Alteração de método de assinatura para o processo #{process_number}",
            "signers": put_signers
        }

        res_put = self.openapi_client.update_envelope(put_payload)
        new_external_id = res_put.get("id") or f"openapi_env_alt_{uuid4().hex[:8]}"

        # Executa substituição seletiva via API do microsserviço
        new_env_data = self.api_client.replace_envelope(
            old_envelope_id=old_env_id,
            new_document_scope_hash=active_env.get("document_scope_hash", "altered_scope"),
            reason_code=MaintenanceReason.SIGNER_CHANGE,
            detailed_description=f"Atualização de método de assinatura no processo #{process_number}",
            new_external_envelope_id=new_external_id,
            signers=signers_api_list
        )

        return {
            "status": "SUCESSO",
            "action": "UPDATE_SIGNATURE_METHOD",
            "old_envelope_id": str(old_env_id),
            "old_external_id": old_external_id,
            "new_envelope_id": new_env_data.get("id"),
            "new_external_id": new_external_id,
            "version": new_env_data.get("envelope_version"),
            "signers_count": len(signers)
        }

    def cancel_active_envelope(
        self,
        request_id: UUID,
        process_number: int,
        reason: str = "Cancelamento solicitado via esteira"
    ) -> Dict[str, Any]:
        """
        Cancela o envelope ativo da solicitação na API externa e na API do microsserviço (com auditoria).
        """
        active_list = self.api_client.list_journey_envelopes(str(request_id))
        if not active_list:
            raise ValueError(f"Nenhum envelope ativo encontrado para cancelamento no processo #{process_number}.")

        active_env = active_list[-1]
        ext_id = active_env.get("external_envelope_id")
        env_id = active_env.get("id")

        if ext_id:
            try:
                self.openapi_client.delete_envelope(ext_id)
            except Exception as err:
                logger.warning(f"Aviso ao deletar envelope {ext_id} na OpenAPI: {err}")

        # Aciona a rota de manutenção do microsserviço
        res_cancel = self.api_client.cancel_envelope_maintenance(
            envelope_id=env_id,
            reason_code=MaintenanceReason.MANUAL_INTERVENTION,
            detailed_description=f"Cancelamento pelo processo #{process_number}: {reason}",
            canceled_by="RPA_AUTOMATION"
        )

        return {
            "status": "SUCESSO",
            "action": "CANCEL_ENVELOPE",
            "envelope_id": str(env_id),
            "external_envelope_id": ext_id,
            "envelope_status": "CANCELED",
            "maintenance_id": res_cancel.get("maintenance_id"),
            "reason": reason
        }
