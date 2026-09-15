"""
Router de Gerenciamento do Ciclo de Vida de Envelopes.
Permite criação, atualização de status e substituição seletiva via API REST.
"""

from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from microservico.api.dependencies import (
    Repositories,
    get_repositories,
    get_rabbitmq_client
)
from microservico.api.schemas import (
    EnvelopeCreateRequest,
    EnvelopeResponse,
    EnvelopeStatusUpdateRequest,
    EnvelopeReplaceRequest
)
from microservico.domain.enums import EnvelopeStatus, MaintenanceReason
from microservico.notifier.rabbitmq_client import RabbitMQClient

router = APIRouter(prefix="/api/v1/envelopes", tags=["Envelopes de Assinatura"])


@router.post("", response_model=EnvelopeResponse, status_code=status.HTTP_201_CREATED, summary="Registra um novo envelope com signatários e documentos")
def create_envelope(
    payload: EnvelopeCreateRequest,
    repos: Repositories = Depends(get_repositories),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Persiste um novo envelope associado à jornada pai.
    Vincula automaticamente associados, documentos e signatários informados no payload.
    """
    # 1. Cria registro na tabela 'envelopes'
    envelope = repos.envelope.create_envelope(
        request_id=payload.request_id,
        document_scope_hash=payload.document_scope_hash,
        provider=payload.provider,
        envelope_version=payload.envelope_version,
        allow_signature_order=payload.allow_signature_order
    )

    if payload.external_envelope_id:
        repos.envelope.update_external_id(
            envelope_id=envelope.id,
            external_envelope_id=payload.external_envelope_id,
            status=EnvelopeStatus.PENDING_SIGNATURE
        )
        envelope = repos.envelope.get_by_id(envelope.id)

    # 2. Registra associados e signatários
    for signer in payload.signers:
        assoc = repos.associate.get_or_create(
            tax_id=signer.tax_id,
            name=signer.name,
            email=signer.email,
            phone=signer.phone
        )
        repos.signer.add_signer(
            envelope_id=envelope.id,
            associate_id=assoc.id,
            signer_role=signer.role,
            signature_order=signer.order,
            signature_type=signer.signature_type,
            validation_channel=signer.validation_channel
        )

    # 3. Registra documentos vinculados ao primeiro associado titular
    first_assoc_id = None
    if payload.signers:
        first_assoc = repos.associate.get_by_tax_id(payload.signers[0].tax_id)
        if first_assoc:
            first_assoc_id = first_assoc.id

    if first_assoc_id:
        for doc in payload.documents:
            repos.document.add_document(
                envelope_id=envelope.id,
                associate_id=first_assoc_id,
                file_name=doc.name,
                source_hash=doc.document_hash,
                extension=doc.name.split(".")[-1] if "." in doc.name else "pdf"
            )

    # 4. Publica evento no RabbitMQ
    rabbitmq.publish_message({
        "event_type": "ENVELOPE_CREATED",
        "envelope_id": str(envelope.id),
        "request_id": str(envelope.request_id),
        "version": envelope.envelope_version,
        "status": envelope.envelope_status.value,
        "external_envelope_id": envelope.external_envelope_id,
        "timestamp": datetime.now().isoformat()
    })

    return EnvelopeResponse(
        id=envelope.id,
        request_id=envelope.request_id,
        document_scope_hash=envelope.document_scope_hash,
        envelope_version=envelope.envelope_version,
        provider=envelope.provider,
        envelope_status=envelope.envelope_status,
        external_envelope_id=envelope.external_envelope_id,
        allow_signature_order=envelope.allow_signature_order,
        is_altered=envelope.is_altered,
        replaced_by_external_id=envelope.replaced_by_external_id,
        sent_at=envelope.sent_at,
        expired_at=envelope.expired_at,
        completed_at=envelope.completed_at,
        created_at=envelope.created_at,
        updated_at=envelope.updated_at
    )


@router.get("/{envelope_id}", response_model=EnvelopeResponse, summary="Consulta um envelope pelo UUID")
def get_envelope_by_id(
    envelope_id: UUID,
    repos: Repositories = Depends(get_repositories)
):
    """
    Recupera os detalhes de um envelope sem necessidade de queries manuais no PostgreSQL.
    """
    envelope = repos.envelope.get_by_id(envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail=f"Envelope '{envelope_id}' não encontrado.")

    return EnvelopeResponse(
        id=envelope.id,
        request_id=envelope.request_id,
        document_scope_hash=envelope.document_scope_hash,
        envelope_version=envelope.envelope_version,
        provider=envelope.provider,
        envelope_status=envelope.envelope_status,
        external_envelope_id=envelope.external_envelope_id,
        allow_signature_order=envelope.allow_signature_order,
        is_altered=envelope.is_altered,
        replaced_by_external_id=envelope.replaced_by_external_id,
        sent_at=envelope.sent_at,
        expired_at=envelope.expired_at,
        completed_at=envelope.completed_at,
        created_at=envelope.created_at,
        updated_at=envelope.updated_at
    )


@router.patch("/{envelope_id}/status", response_model=EnvelopeResponse, summary="Atualiza o status e ID externo do envelope")
def update_envelope_status(
    envelope_id: UUID,
    payload: EnvelopeStatusUpdateRequest,
    repos: Repositories = Depends(get_repositories),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Atualiza o estado de um envelope (ex: PENDING_SIGNATURE, COMPLETED, CANCELED).
    Se informado `external_envelope_id`, vincula o identificador da OpenAPI.
    """
    envelope = repos.envelope.get_by_id(envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail=f"Envelope '{envelope_id}' não encontrado.")

    if payload.external_envelope_id:
        repos.envelope.update_external_id(
            envelope_id=envelope_id,
            external_envelope_id=payload.external_envelope_id,
            status=payload.envelope_status
        )
    else:
        repos.envelope.update_status(envelope_id, payload.envelope_status)

    updated_env = repos.envelope.get_by_id(envelope_id)

    # Publica evento de atualização no RabbitMQ
    rabbitmq.publish_message({
        "event_type": "ENVELOPE_STATUS_UPDATED",
        "envelope_id": str(envelope_id),
        "request_id": str(updated_env.request_id),
        "previous_status": envelope.envelope_status.value,
        "new_status": updated_env.envelope_status.value,
        "external_envelope_id": updated_env.external_envelope_id,
        "timestamp": datetime.now().isoformat()
    })

    return EnvelopeResponse(
        id=updated_env.id,
        request_id=updated_env.request_id,
        document_scope_hash=updated_env.document_scope_hash,
        envelope_version=updated_env.envelope_version,
        provider=updated_env.provider,
        envelope_status=updated_env.envelope_status,
        external_envelope_id=updated_env.external_envelope_id,
        allow_signature_order=updated_env.allow_signature_order,
        is_altered=updated_env.is_altered,
        replaced_by_external_id=updated_env.replaced_by_external_id,
        sent_at=updated_env.sent_at,
        expired_at=updated_env.expired_at,
        completed_at=updated_env.completed_at,
        created_at=updated_env.created_at,
        updated_at=updated_env.updated_at
    )


@router.post("/{envelope_id}/replace", response_model=EnvelopeResponse, summary="Executa a substituição seletiva de um envelope")
def replace_envelope(
    envelope_id: UUID,
    payload: EnvelopeReplaceRequest,
    repos: Repositories = Depends(get_repositories),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Substituição Seletiva:
    1. Marca o envelope anterior como REPLACED_CANCELED (ou ALTERADO com vínculo).
    2. Calcula a nova versão incremental (max_v + 1).
    3. Cria o novo envelope com os novos documentos e participantes.
    4. Registra auditoria imediata na tabela 'maintenance_history'.
    5. Publica evento no RabbitMQ.
    """
    old_env = repos.envelope.get_by_id(envelope_id)
    if not old_env:
        raise HTTPException(status_code=404, detail=f"Envelope obsoleto '{envelope_id}' não encontrado.")

    # 1. Marca envelope antigo como REPLACED_CANCELED
    repos.envelope.mark_replaced_cancelled(envelope_id)
    if payload.new_external_envelope_id:
        repos.envelope.mark_altered(envelope_id, payload.new_external_envelope_id)

    # 2. Calcula nova versão
    max_v = repos.envelope.get_max_version_by_request(old_env.request_id)
    new_version = max_v + 1

    # 3. Cria novo envelope
    new_env = repos.envelope.create_envelope(
        request_id=old_env.request_id,
        document_scope_hash=payload.new_document_scope_hash,
        provider=old_env.provider,
        envelope_version=new_version,
        allow_signature_order=old_env.allow_signature_order
    )

    if payload.new_external_envelope_id:
        repos.envelope.update_external_id(
            envelope_id=new_env.id,
            external_envelope_id=payload.new_external_envelope_id,
            status=EnvelopeStatus.PENDING_SIGNATURE
        )
        new_env = repos.envelope.get_by_id(new_env.id)

    # 4. Registra auditoria na maintenance_history
    repos.maintenance.log_maintenance(
        request_id=old_env.request_id,
        envelope_id=new_env.id,
        reason_code=payload.reason_code,
        detailed_description=f"Substituição do envelope {old_env.id} (v{old_env.envelope_version}) pela v{new_version}. Motivo: {payload.detailed_description}"
    )

    # 5. Publica evento no RabbitMQ
    rabbitmq.publish_message({
        "event_type": "ENVELOPE_REPLACED",
        "old_envelope_id": str(old_env.id),
        "new_envelope_id": str(new_env.id),
        "request_id": str(old_env.request_id),
        "new_version": new_version,
        "reason_code": payload.reason_code.value,
        "operator": payload.operator_name,
        "timestamp": datetime.now().isoformat()
    })

    return EnvelopeResponse(
        id=new_env.id,
        request_id=new_env.request_id,
        document_scope_hash=new_env.document_scope_hash,
        envelope_version=new_env.envelope_version,
        provider=new_env.provider,
        envelope_status=new_env.envelope_status,
        external_envelope_id=new_env.external_envelope_id,
        allow_signature_order=new_env.allow_signature_order,
        is_altered=new_env.is_altered,
        replaced_by_external_id=new_env.replaced_by_external_id,
        sent_at=new_env.sent_at,
        expired_at=new_env.expired_at,
        completed_at=new_env.completed_at,
        created_at=new_env.created_at,
        updated_at=new_env.updated_at
    )
