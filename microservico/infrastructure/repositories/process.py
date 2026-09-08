"""
Módulo do Repositório de Processos (ProcessRepository).
Gerencia a busca e criação de tipos de processo na tabela 'processes'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from microservico.domain.models import ProcessModel
from microservico.infrastructure.repositories.base import BaseRepository


class ProcessRepository(BaseRepository):
    """
    Repositório para gerenciamento da tabela de processos (processes).

    Controla o catálogo de processos da esteira de crédito e serviços Sicredi.
    """

    def _to_model(self, data: dict) -> ProcessModel:
        """Converte dicionário de colunas para a entidade ProcessModel."""
        return ProcessModel(
            id=UUID(str(data["id"])),
            name=data["name"],
            description=data.get("description"),
            active=bool(data.get("active", True)),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def get_by_id(self, process_id: UUID) -> Optional[ProcessModel]:
        """
        Recupera um processo pelo seu identificador primário.

        Parâmetros:
            process_id (UUID): Identificador único do processo.

        Retorno:
            Optional[ProcessModel]: Processo encontrado ou None.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM processes WHERE id = %s",
            (process_id,)
        )
        return self._to_model(row) if row else None

    def get_or_create(self, name: str, description: Optional[str] = None) -> ProcessModel:
        """
        Busca um processo pelo nome ou cria um novo registro se não existir.

        Parâmetros:
            name (str): Nome identificador do processo.
            description (Optional[str]): Descrição detalhada do processo.

        Retorno:
            ProcessModel: Entidade do processo persistida.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM processes WHERE name = %s",
            (name,)
        )
        if row:
            return self._to_model(row)

        new_id = uuid4()
        now = datetime.now()
        self.db_manager.execute(
            "INSERT INTO processes (id, name, description, active, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (new_id, name, description, True, now, now)
        )
        created = self.get_by_id(new_id)
        return created if created is not None else ProcessModel(
            id=new_id,
            name=name,
            description=description,
            active=True,
            created_at=now,
            updated_at=now
        )
