"""
Módulo do Repositório de Jornadas (JourneyRepository).
Gerencia a persistência e atualização de solicitações documentais na tabela 'journey_requests'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from microservico.domain.enums import JourneyStatus
from microservico.domain.models import JourneyRequestModel
from microservico.infrastructure.repositories.base import BaseRepository


class JourneyRepository(BaseRepository):
    """
    Repositório de jornadas e solicitações documentais (journey_requests).

    Responsável pelo registro idempotente via mongo_id e transições de status.
    """

    def _to_model(self, data: dict) -> JourneyRequestModel:
        """Converte dicionário de colunas para a entidade JourneyRequestModel."""
        parsed = self._parse_row(data)
        assert parsed is not None
        return JourneyRequestModel(
            id=UUID(str(parsed["id"])),
            process_id=UUID(str(parsed["process_id"])),
            mongo_id=parsed["mongo_id"],
            process_number=int(parsed["process_number"]),
            fluid_payload=parsed.get("fluid_payload", {}),
            initial_id=parsed.get("initial_id"),
            status=JourneyStatus(parsed["status"]),
            details=parsed.get("details"),
            executions=int(parsed.get("executions", 1)),
            created_at=parsed.get("created_at"),
            updated_at=parsed.get("updated_at")
        )

    def get_by_id(self, journey_id: UUID) -> Optional[JourneyRequestModel]:
        """
        Recupera uma jornada pelo identificador primário.

        Parâmetros:
            journey_id (UUID): Identificador único da jornada.

        Retorno:
            Optional[JourneyRequestModel]: Jornada encontrada ou None.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM journey_requests WHERE id = %s",
            (journey_id,)
        )
        return self._to_model(row) if row else None

    def get_by_mongo_id(self, mongo_id: str) -> Optional[JourneyRequestModel]:
        """
        Busca uma jornada pelo identificador único do MongoDB.

        Parâmetros:
            mongo_id (str): ID do documento no MongoDB/Fluid.

        Retorno:
            Optional[JourneyRequestModel]: Objeto da jornada ou None.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM journey_requests WHERE mongo_id = %s",
            (mongo_id,)
        )
        return self._to_model(row) if row else None

    def create_journey(
        self,
        process_id: UUID,
        mongo_id: str,
        process_number: int,
        fluid_payload: Dict[str, Any],
        initial_id: Optional[str] = None
    ) -> JourneyRequestModel:
        """
        Registra uma nova jornada de solicitação de forma idempotente por mongo_id.

        Parâmetros:
            process_id (UUID): Identificador do tipo de processo.
            mongo_id (str): Identificador único da tarefa no MongoDB.
            process_number (int): Número do processo no Fluid.
            fluid_payload (Dict[str, Any]): Metadados completos da solicitação.
            initial_id (Optional[str]): ID de controle inicial se aplicável.

        Retorno:
            JourneyRequestModel: Registro da jornada persistida.
        """
        existing = self.get_by_mongo_id(mongo_id)
        if existing:
            return existing

        new_id = uuid4()
        now = datetime.now()
        self.db_manager.execute(
            "INSERT INTO journey_requests (id, process_id, mongo_id, process_number, initial_id, fluid_payload, status, executions, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                new_id,
                process_id,
                mongo_id,
                process_number,
                initial_id,
                fluid_payload,
                JourneyStatus.RECEIVED,
                1,
                now,
                now
            )
        )
        created = self.get_by_mongo_id(mongo_id)
        return created if created is not None else JourneyRequestModel(
            id=new_id,
            process_id=process_id,
            mongo_id=mongo_id,
            process_number=process_number,
            fluid_payload=fluid_payload,
            initial_id=initial_id,
            status=JourneyStatus.RECEIVED,
            executions=1,
            created_at=now,
            updated_at=now
        )

    def update_status(
        self,
        journey_id: UUID,
        status: JourneyStatus,
        details: Optional[str] = None
    ) -> None:
        """
        Atualiza o estado de processamento de uma jornada.

        Parâmetros:
            journey_id (UUID): Identificador da jornada.
            status (JourneyStatus): Novo status a ser aplicado.
            details (Optional[str]): Detalhes ou histórico do processamento.
        """
        now = datetime.now()
        self.db_manager.execute(
            "UPDATE journey_requests SET status = %s, details = %s, updated_at = %s WHERE id = %s",
            (status, details, now, journey_id)
        )
