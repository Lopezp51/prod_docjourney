"""
Router de Gerenciamento de Jornadas (Journey Requests).
Permite criar, consultar e atualizar jornadas vindas do MongoDB/Fluid via REST.
"""

from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status

from microservico.api.dependencies import Repositories, get_repositories
from microservico.api.schemas import (
    JourneyCreateRequest,
    JourneyResponse,
    EnvelopeResponse
)
from microservico.domain.enums import JourneyStatus

router = APIRouter(prefix="/api/v1/journeys", tags=["Jornadas e Solicitações"])


@router.post("", response_model=JourneyResponse, status_code=status.HTTP_201_CREATED, summary="Registra ou recupera uma jornada pelo mongo_id")
def get_or_create_journey(
    payload: JourneyCreateRequest,
    repos: Repositories = Depends(get_repositories)
):
    """
    Registra uma nova jornada de solicitação de forma idempotente.
    Se a jornada com o mesmo `mongo_id` já existir no banco, ela é retornada imediatamente.
    """
    # 1. Garante a existência do tipo de processo no catálogo
    process = repos.process.get_or_create(name=payload.process_name)

    # 2. Cria ou recupera a jornada
    journey = repos.journey.create_journey(
        process_id=process.id,
        mongo_id=payload.mongo_id,
        process_number=payload.process_number,
        fluid_payload=payload.fluid_payload,
        initial_id=payload.initial_id
    )

    return JourneyResponse(
        id=journey.id,
        process_id=journey.process_id,
        mongo_id=journey.mongo_id,
        process_number=journey.process_number,
        initial_id=journey.initial_id,
        journey_status=journey.status,
        retry_count=journey.executions,
        created_at=journey.created_at,
        updated_at=journey.updated_at
    )


@router.get("/{mongo_id}", response_model=JourneyResponse, summary="Busca uma jornada pelo mongo_id")
def get_journey_by_mongo_id(
    mongo_id: str,
    repos: Repositories = Depends(get_repositories)
):
    """
    Recupera os dados cadastrais e status atual de uma jornada pelo seu `mongo_id`.
    Evita a necessidade de rodar queries manuais: SELECT * FROM journey_requests WHERE mongo_id = ?
    """
    journey = repos.journey.get_by_mongo_id(mongo_id)
    if not journey:
        raise HTTPException(status_code=404, detail=f"Jornada com mongo_id '{mongo_id}' não encontrada.")

    return JourneyResponse(
        id=journey.id,
        process_id=journey.process_id,
        mongo_id=journey.mongo_id,
        process_number=journey.process_number,
        initial_id=journey.initial_id,
        journey_status=journey.status,
        retry_count=journey.executions,
        created_at=journey.created_at,
        updated_at=journey.updated_at
    )


@router.patch("/{journey_id}/status", response_model=dict, summary="Atualiza o status de uma jornada")
def update_journey_status(
    journey_id: UUID,
    status_value: JourneyStatus,
    details: str = None,
    repos: Repositories = Depends(get_repositories)
):
    """
    Atualiza o estado de uma jornada (ex.: IN_PROCESS, COMPLETED, INTERVENTION, FAILED).
    """
    journey = repos.journey.get_by_id(journey_id)
    if not journey:
        raise HTTPException(status_code=404, detail=f"Jornada com ID '{journey_id}' não encontrada.")

    repos.journey.update_status(journey_id, status=status_value, details=details)
    return {"message": f"Status da jornada {journey_id} atualizado para {status_value.value}."}


@router.get("/{journey_id}/envelopes", response_model=List[EnvelopeResponse], summary="Lista os envelopes ativos de uma jornada")
def list_journey_envelopes(
    journey_id: UUID,
    repos: Repositories = Depends(get_repositories)
):
    """
    Lista todos os envelopes ativos vinculados a uma jornada, permitindo à automação
    avaliar a necessidade de substituição seletiva sem fazer queries diretas no banco.
    """
    envelopes = repos.envelope.list_active_by_request(journey_id)
    return [
        EnvelopeResponse(
            id=env.id,
            request_id=env.request_id,
            document_scope_hash=env.document_scope_hash,
            envelope_version=env.envelope_version,
            provider=env.provider,
            envelope_status=env.envelope_status,
            external_envelope_id=env.external_envelope_id,
            allow_signature_order=env.allow_signature_order,
            is_altered=env.is_altered,
            replaced_by_external_id=env.replaced_by_external_id,
            sent_at=env.sent_at,
            expired_at=env.expired_at,
            completed_at=env.completed_at,
            created_at=env.created_at,
            updated_at=env.updated_at
        )
        for env in envelopes
    ]
