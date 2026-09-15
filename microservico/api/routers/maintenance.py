"""
Router de Governança, Auditoria e Manutenção Operacional (Maintenance & Governance API).
Elimina a necessidade de operadores, esteiras ou desenvolvedores realizarem consultas
ou comandos SQL manuais diretamente no banco de dados PostgreSQL.
"""

from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status

from microservico.api.dependencies import (
    Repositories,
    get_repositories,
    get_rabbitmq_client
)
from microservico.api.schemas import (
    MaintenanceCancelRequest,
    MaintenanceExpireCheckResponse,
    MaintenanceHistoryResponse,
    MaintenanceResolveRequest,
    MaintenanceOverviewResponse
)
from microservico.domain.enums import EnvelopeStatus, MaintenanceReason
from microservico.notifier.rabbitmq_client import RabbitMQClient

router = APIRouter(prefix="/api/v1/maintenance", tags=["Governança e Manutenção"])


@router.post("/cancel", response_model=dict, summary="Cancela um envelope administrativamente e audita na maintenance_history")
def cancel_envelope(
    payload: MaintenanceCancelRequest,
    repos: Repositories = Depends(get_repositories),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Executa o cancelamento administrativo de um envelope com governança e auditoria total:
    1. Atualiza o status do envelope para CANCELED no banco.
    2. Registra log detalhado na tabela 'maintenance_history'.
    3. Publica evento de cancelamento no RabbitMQ.
    
    Substitui queries manuais como:
    UPDATE envelopes SET envelope_status = 'CANCELED' WHERE id = ...;
    INSERT INTO maintenance_history ...;
    """
    envelope = repos.envelope.get_by_id(payload.envelope_id)
    if not envelope:
        raise HTTPException(status_code=404, detail=f"Envelope '{payload.envelope_id}' não encontrado.")

    # 1. Atualiza status do envelope
    repos.envelope.update_status(payload.envelope_id, EnvelopeStatus.CANCELED)

    # 2. Grava auditoria
    log = repos.maintenance.log_maintenance(
        request_id=envelope.request_id,
        envelope_id=envelope.id,
        reason_code=payload.reason_code,
        detailed_description=f"Cancelado por {payload.canceled_by}. Justificativa: {payload.detailed_description}"
    )

    # 3. Publica evento no RabbitMQ
    rabbitmq.publish_message({
        "event_type": "ENVELOPE_CANCELED",
        "envelope_id": str(envelope.id),
        "request_id": str(envelope.request_id),
        "canceled_by": payload.canceled_by,
        "reason_code": payload.reason_code.value,
        "maintenance_id": str(log.id),
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "SUCCESS",
        "message": f"Envelope {payload.envelope_id} cancelado com sucesso.",
        "maintenance_id": str(log.id),
        "envelope_status": EnvelopeStatus.CANCELED.value
    }


@router.post("/expire-check", response_model=MaintenanceExpireCheckResponse, summary="Varre e expira envelopes com mais de 60 dias sem assinatura")
def run_expiration_check(
    repos: Repositories = Depends(get_repositories),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Rotina de expiração automática (substitui scripts manuais SQL):
    1. Localiza todos os envelopes com status PENDING_SIGNATURE cujo prazo expirou (expired_at <= NOW()).
    2. Altera o status para EXPIRED.
    3. Grava registro na tabela 'maintenance_history' com reason_code = 'EXPIRED_60_DAYS'.
    4. Notifica via mensageria RabbitMQ.
    """
    expired_envelopes = repos.envelope.list_expired_over_60_days()
    expired_ids: List[UUID] = []

    for env in expired_envelopes:
        # Atualiza status
        repos.envelope.update_status(env.id, EnvelopeStatus.EXPIRED)
        expired_ids.append(env.id)

        # Grava auditoria
        repos.maintenance.log_maintenance(
            request_id=env.request_id,
            envelope_id=env.id,
            reason_code=MaintenanceReason.EXPIRED_60_DAYS,
            detailed_description=f"Envelope expirado automaticamente por atingir o limite de vigência ({env.expired_at})."
        )

        # Dispara evento RabbitMQ
        rabbitmq.publish_message({
            "event_type": "ENVELOPE_EXPIRED",
            "envelope_id": str(env.id),
            "request_id": str(env.request_id),
            "external_envelope_id": env.external_envelope_id,
            "expired_at": env.expired_at.isoformat() if env.expired_at else None,
            "timestamp": datetime.now().isoformat()
        })

    return MaintenanceExpireCheckResponse(
        expired_count=len(expired_ids),
        expired_envelope_ids=expired_ids,
        processed_at=datetime.now(),
        message=f"Rotina concluída: {len(expired_ids)} envelopes expirados identificados e atualizados."
    )


@router.get("/history", response_model=List[MaintenanceHistoryResponse], summary="Consulta histórico de ocorrências e auditoria com filtros")
def get_maintenance_history(
    reason_code: Optional[str] = Query(None, description="Filtrar por código do motivo (ex: EXPIRED_60_DAYS, CORRUPTED_DOCUMENT)"),
    resolved: Optional[bool] = Query(None, description="Filtrar por status de resolução (true/false)"),
    request_id: Optional[UUID] = Query(None, description="Filtrar por UUID da jornada pai"),
    envelope_id: Optional[UUID] = Query(None, description="Filtrar por UUID do envelope"),
    limit: int = Query(50, ge=1, le=500, description="Limite máximo de registros"),
    offset: int = Query(0, ge=0, description="Deslocamento para paginação"),
    repos: Repositories = Depends(get_repositories)
):
    """
    Retorna logs da tabela 'maintenance_history' de forma estruturada.
    Elimina queries manuais do tipo:
    SELECT * FROM maintenance_history WHERE reason_code = ... AND resolved = ...
    """
    records = repos.maintenance.list_history(
        reason_code=reason_code,
        resolved=resolved,
        request_id=request_id,
        envelope_id=envelope_id,
        limit=limit,
        offset=offset
    )

    return [
        MaintenanceHistoryResponse(
            id=r.id,
            request_id=r.request_id,
            envelope_id=r.envelope_id,
            reason_code=r.reason_code.value if hasattr(r.reason_code, "value") else str(r.reason_code),
            detailed_description=r.detailed_description,
            resolved=r.resolved,
            resolved_by=r.resolved_by,
            created_at=r.created_at,
            updated_at=r.updated_at
        )
        for r in records
    ]


@router.patch("/history/{maintenance_id}/resolve", response_model=dict, summary="Marca uma pendência de manutenção como saneada/resolvida")
def resolve_maintenance_item(
    maintenance_id: UUID,
    payload: MaintenanceResolveRequest,
    repos: Repositories = Depends(get_repositories),
    rabbitmq: RabbitMQClient = Depends(get_rabbitmq_client)
):
    """
    Saneia um registro de intervenção ou falha na tabela maintenance_history.
    Substitui: UPDATE maintenance_history SET resolved = TRUE, resolved_by = ? WHERE id = ?
    """
    record = repos.maintenance.get_by_id(maintenance_id)
    if not record:
        raise HTTPException(status_code=404, detail=f"Registro de manutenção '{maintenance_id}' não encontrado.")

    repos.maintenance.resolve_maintenance(maintenance_id, resolved_by=payload.resolved_by)

    # Publica evento de resolução no RabbitMQ
    rabbitmq.publish_message({
        "event_type": "MAINTENANCE_RESOLVED",
        "maintenance_id": str(maintenance_id),
        "resolved_by": payload.resolved_by,
        "comment": payload.comment,
        "timestamp": datetime.now().isoformat()
    })

    return {
        "status": "SUCCESS",
        "message": f"Ocorrência de manutenção {maintenance_id} marcada como resolvida por {payload.resolved_by}."
    }


@router.get("/overview", response_model=MaintenanceOverviewResponse, summary="Dashboard de métricas operacionais e governança em tempo real")
def get_maintenance_overview(
    repos: Repositories = Depends(get_repositories)
):
    """
    Visão consolidada para monitoramento:
    - Quantidade de jornadas por status
    - Quantidade de envelopes por status
    - Total de intervenções pendentes de saneamento humano
    """
    total_j = repos.journey.count_total()
    j_by_status = repos.journey.count_by_status()

    total_e = repos.envelope.count_total()
    e_by_status = repos.envelope.count_by_status()

    unresolved_m = repos.maintenance.count_unresolved()
    total_m = repos.maintenance.count_total()

    return MaintenanceOverviewResponse(
        total_journeys=total_j,
        journeys_by_status=j_by_status,
        total_envelopes=total_e,
        envelopes_by_status=e_by_status,
        unresolved_maintenance_incidents=unresolved_m,
        total_maintenance_incidents=total_m,
        timestamp=datetime.now()
    )
