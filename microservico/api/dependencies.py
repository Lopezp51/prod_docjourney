"""
Módulo de Injeção de Dependências da API FastAPI.
Fornece instâncias seguras e gerenciadas de conexão com o banco de dados,
repositórios de dados e cliente RabbitMQ.
"""

from typing import Generator
from fastapi import Depends

from microservico.config import config
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.infrastructure.repositories import (
    JourneyRepository,
    ProcessRepository,
    EnvelopeRepository,
    AssociateRepository,
    DocumentRepository,
    EnvelopeSignerRepository,
    MaintenanceHistoryRepository
)
from microservico.notifier.rabbitmq_client import RabbitMQClient

_db_manager_instance: DatabaseManager = None
_rabbitmq_instance: RabbitMQClient = None


def get_db_manager() -> DatabaseManager:
    """
    Retorna uma instância singleton gerenciada de conexão ao banco.
    Usa SQLite em memória se configurado, ou PostgreSQL por padrão.
    """
    global _db_manager_instance
    if _db_manager_instance is None:
        use_sqlite = config.DB_HOST == "sqlite" or getattr(config, "USE_SQLITE", False)
        if use_sqlite:
            _db_manager_instance = DatabaseManager(use_sqlite=True)
        else:
            dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
            _db_manager_instance = DatabaseManager(dsn=dsn, use_sqlite=False)
        initialize_database_if_empty(_db_manager_instance)
    return _db_manager_instance


def set_db_manager(custom_manager: DatabaseManager) -> None:
    """Permite sobrescrever a instância de banco (útil para testes com SQLite)."""
    global _db_manager_instance
    _db_manager_instance = custom_manager


def get_rabbitmq_client() -> RabbitMQClient:
    """Retorna o cliente resiliente RabbitMQ."""
    global _rabbitmq_instance
    if _rabbitmq_instance is None:
        _rabbitmq_instance = RabbitMQClient()
    return _rabbitmq_instance


class Repositories:
    """Agrupador de repositórios para injeção limpa nos endpoints."""

    def __init__(self, db: DatabaseManager = Depends(get_db_manager)):
        self.journey = JourneyRepository(db)
        self.process = ProcessRepository(db)
        self.envelope = EnvelopeRepository(db)
        self.associate = AssociateRepository(db)
        self.document = DocumentRepository(db)
        self.signer = EnvelopeSignerRepository(db)
        self.maintenance = MaintenanceHistoryRepository(db)


def get_repositories(repos: Repositories = Depends()) -> Repositories:
    """Injeta o container de repositórios nos routers."""
    return repos
