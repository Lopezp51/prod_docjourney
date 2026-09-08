"""
Módulo Base de Repositórios Relacionais (BaseRepository).
Define a infraestrutura compartilhada e métodos utilitários para conversão de registros.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
from typing import Any, Dict, Optional
from microservico.infrastructure.db import DatabaseManager


class BaseRepository:
    """
    Classe base para todos os repositórios do sistema.

    Armazena a referência para o DatabaseManager e provê utilitários
    de deserialização de campos JSON/JSONB e normalização de registros.
    """

    def __init__(self, db_manager: DatabaseManager):
        """
        Inicializa o repositório base com a instância do gerenciador de banco.

        Parâmetros:
            db_manager (DatabaseManager): Gerenciador centralizado de banco de dados.
        """
        self.db_manager = db_manager

    def _parse_row(self, row: Any) -> Optional[Dict[str, Any]]:
        """
        Converte uma linha de resultado do cursor para um dicionário padronizado.

        Deserializa automaticamente campos JSON stringificados se presentes.

        Parâmetros:
            row (Any): Linha retornada pelo cursor do banco de dados.

        Retorno:
            Optional[Dict[str, Any]]: Dicionário com colunas e valores ou None.
        """
        if row is None:
            return None
        data = dict(row)
        if "fluid_payload" in data and isinstance(data["fluid_payload"], str):
            try:
                data["fluid_payload"] = json.loads(data["fluid_payload"])
            except Exception:
                pass
        return data
