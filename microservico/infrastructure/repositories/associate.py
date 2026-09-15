"""
Módulo do Repositório de Associados (AssociateRepository).
Gerencia a persistência e busca de pessoas físicas e jurídicas na tabela 'associates'.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from microservico.domain.models import AssociateModel
from microservico.infrastructure.repositories.base import BaseRepository


class AssociateRepository(BaseRepository):
    """
    Repositório para gerenciamento da tabela de associados (associates).

    Responsável pela busca por CPF/CNPJ e inserção/atualização idempotente (upsert).
    """

    def _to_model(self, data: dict) -> AssociateModel:
        """Converte dicionário de colunas para a entidade de domínio AssociateModel."""
        return AssociateModel(
            id=UUID(str(data["id"])),
            tax_id=data["tax_id"],
            name=data["name"],
            email=data.get("email"),
            phone=data.get("phone"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

    def get_by_tax_id(self, tax_id: str) -> Optional[AssociateModel]:
        """
        Recupera um associado pelo seu CPF ou CNPJ único.

        Parâmetros:
            tax_id (str): Número do documento (CPF ou CNPJ).

        Retorno:
            Optional[AssociateModel]: Objeto do associado encontrado ou None.
        """
        row = self.db_manager.fetch_one(
            "SELECT * FROM associates WHERE tax_id = %s",
            (tax_id,)
        )
        return self._to_model(row) if row else None

    def upsert(
        self,
        tax_id: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> AssociateModel:
        """
        Insere ou atualiza os dados de um associado pelo CPF/CNPJ de forma idempotente.

        Parâmetros:
            tax_id (str): Documento CPF ou CNPJ.
            name (str): Nome completo ou razão social.
            email (Optional[str]): E-mail para contato e assinaturas.
            phone (Optional[str]): Telefone celular com DDD.

        Retorno:
            AssociateModel: Instância atualizada do associado.
        """
        existing = self.get_by_tax_id(tax_id)
        now = datetime.now()

        if existing:
            self.db_manager.execute(
                "UPDATE associates SET name = %s, email = %s, phone = %s, updated_at = %s WHERE tax_id = %s",
                (name, email, phone, now, tax_id)
            )
            updated = self.get_by_tax_id(tax_id)
            return updated if updated is not None else existing

        new_id = uuid4()
        self.db_manager.execute(
            "INSERT INTO associates (id, tax_id, name, email, phone, created_at, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (new_id, tax_id, name, email, phone, now, now)
        )
        created = self.get_by_tax_id(tax_id)
        return created if created is not None else AssociateModel(
            id=new_id,
            tax_id=tax_id,
            name=name,
            email=email,
            phone=phone,
            created_at=now,
            updated_at=now
        )

    def get_or_create(
        self,
        tax_id: str,
        name: str,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> AssociateModel:
        """Alias para upsert de associado."""
        return self.upsert(tax_id=tax_id, name=name, email=email, phone=phone)

