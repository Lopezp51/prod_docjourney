"""
Pacote de Repositórios Relacionais de Infraestrutura (microservico.infrastructure.repositories).
Fornece acesso desacoplado a todas as entidades do banco de dados relacional.
Nomes 100% em inglês com docstrings explicativas em português.
"""

from .base import BaseRepository
from .associate import AssociateRepository
from .process import ProcessRepository
from .journey import JourneyRepository
from .envelope import EnvelopeRepository
from .document import DocumentRepository
from .envelope_signer import EnvelopeSignerRepository
from .maintenance_history import MaintenanceHistoryRepository

__all__ = [
    "BaseRepository",
    "AssociateRepository",
    "ProcessRepository",
    "JourneyRepository",
    "EnvelopeRepository",
    "DocumentRepository",
    "EnvelopeSignerRepository",
    "MaintenanceHistoryRepository",
]
