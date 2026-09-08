"""
Módulo do Repositório de Histórico de Manutenção (MaintenanceHistoryRepository).
Gerencia os registros de auditoria e intervenções na tabela 'maintenance_history'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from microservico.domain.enums import MaintenanceReason
from microservico.domain.models import MaintenanceHistoryModel
from microservico.infrastructure.repositories.base import BaseRepository


class MaintenanceHistoryRepository(BaseRepository):
    """
    Repositório para registro e resolução de histórico de manutenção (maintenance_history).

    Audita pendências de validação, documentos corrompidos e intervenções manuais.
    """

    def _to_model(self, data: dict) -> MaintenanceHistoryModel:
        """Converte dicionário de colunas para a entidade MaintenanceHistoryModel."""
        return MaintenanceHistoryModel(
            id=UUID(str(data["id"])),
            request_id=UUID(str(data["request_id"])),
            envelope_id=UUID(str(data["envelope_id"])) if data.get("envelope_id") else None,
            reason_code=MaintenanceReason(data["reason_code"]),
            detailed_description=data["detailed_description"],
            resolved=bool(data.get("resolved", False)),
            resolved_by=data.get("resolved_by"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def log_maintenance(
        self,
        request_id: UUID,
        reason_code: MaintenanceReason,
        detailed_description: str,
        envelope_id: Optional[UUID] = None
    ) -> MaintenanceHistoryModel:
        """
        Registra uma ocorrência de manutenção ou intervenção para auditoria e controle.

        Parâmetros:
            request_id (UUID): Identificador da solicitação afetada.
            reason_code (MaintenanceReason): Código do motivo de manutenção.
            detailed_description (str): Descrição detalhada do problema ou parecer.
            envelope_id (Optional[UUID]): ID do envelope afetado, se houver.

        Retorno:
            MaintenanceHistoryModel: Registro do log persistido.
        """
        new_id = uuid4()
        now = datetime.now()

        self.db_manager.execute(
            "INSERT INTO maintenance_history (id, request_id, envelope_id, reason_code, detailed_description, resolved, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (
                new_id,
                request_id,
                envelope_id,
                reason_code,
                detailed_description,
                False,
                now,
                now
            )
        )
        return MaintenanceHistoryModel(
            id=new_id,
            request_id=request_id,
            envelope_id=envelope_id,
            reason_code=reason_code,
            detailed_description=detailed_description,
            resolved=False,
            created_at=now,
            updated_at=now
        )

    def resolve_maintenance(self, maintenance_id: UUID, resolved_by: str = "AUTOMATION") -> None:
        """
        Marca um registro de manutenção como resolvido e saneado.

        Parâmetros:
            maintenance_id (UUID): Identificador do registro de manutenção.
            resolved_by (str): Identificador do agente que saneou a ocorrência.
        """
        now = datetime.now()
        self.db_manager.execute(
            "UPDATE maintenance_history SET resolved = TRUE, resolved_by = %s, updated_at = %s WHERE id = %s",
            (resolved_by, now, maintenance_id)
        )
