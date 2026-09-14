"""
Módulo de Gerenciamento de Conexões e Sessões de Banco de Dados.
Fornece suporte desacoplado e unificado a PostgreSQL (produção/homologação) e SQLite em memória (testes).
Abstrai diferenças de dialetos (%s vs ?), normalização de tipos e controle seguro de conexões via Context Managers.
Nomes de métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Tuple
from uuid import UUID

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:
    psycopg = None
    dict_row = None


class DatabaseManager:
    """
    Gerenciador centralizado de conexões, dialetos e sessões transacionais.

    Responsabilidades (SRP & DIP):
    1. Fornecer sessões seguras com commit e rollback automáticos via context manager.
    2. Abstrair as diferenças de dialeto entre PostgreSQL (%s) e SQLite (?).
    3. Normalizar tipos complexos (UUID, datetime, Enums, JSON) para os respectivos drivers.
    4. Garantir liberação e fechamento rigoroso de conexões (prevenção de connection leaks).
    """

    def __init__(self, dsn: Optional[str] = None, use_sqlite: bool = False):
        """
        Inicializa o gerenciador de banco de dados.

        Parâmetros:
            dsn (Optional[str]): String de conexão (Data Source Name) para PostgreSQL.
            use_sqlite (bool): Se True, ativa o modo SQLite em memória para testes rápidos.
        """
        self.dsn = dsn
        self.use_sqlite = use_sqlite
        self._sqlite_conn: Optional[sqlite3.Connection] = None

    def get_connection(self) -> Any:
        """
        Obtém uma conexão ativa com o banco de dados configurado.

        Retorno:
            Any: Conexão ativa do psycopg (PostgreSQL) ou sqlite3 (SQLite).

        Exceções:
            ImportError: Lançado caso psycopg não esteja instalado em ambiente PostgreSQL.
        """
        if self.use_sqlite:
            if self._sqlite_conn is None:
                self._sqlite_conn = sqlite3.connect(":memory:")
                self._sqlite_conn.row_factory = sqlite3.Row
                self._sqlite_conn.execute("PRAGMA foreign_keys = ON;")
            return self._sqlite_conn

        if psycopg is None:
            raise ImportError(
                "O pacote 'psycopg' não está instalado. Instale com: pip install 'psycopg[binary]'"
            )
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def _prepare_query_and_params(
        self,
        query: str,
        params: Tuple[Any, ...] = ()
    ) -> Tuple[str, Tuple[Any, ...]]:
        """
        Normaliza os marcadores de parâmetros e tipos de dados de acordo com o dialeto ativo.

        Parâmetros:
            query (str): Instrução SQL escrita no formato padrão com marcadores '%s'.
            params (Tuple[Any, ...]): Tupla com os valores dos parâmetros.

        Retorno:
            Tuple[str, Tuple[Any, ...]]: Par de query adaptada e parâmetros normalizados.
        """
        converted_params = []
        for p in params:
            if isinstance(p, Enum):
                converted_params.append(p.value)
            elif isinstance(p, UUID):
                converted_params.append(str(p))
            elif isinstance(p, datetime):
                converted_params.append(p.isoformat() if self.use_sqlite else p)
            elif isinstance(p, (dict, list)):
                converted_params.append(json.dumps(p) if self.use_sqlite else json.dumps(p))
            else:
                converted_params.append(p)

        if self.use_sqlite:
            adapted_query = query.replace("%s", "?")
            return adapted_query, tuple(converted_params)

        return query, tuple(converted_params)

    @contextmanager
    def session(self) -> Generator[Any, None, None]:
        """
        Context manager que provê um cursor transacional seguro com commit/rollback e liberação de recursos.

        Yields:
            Any: Cursor ativo para execução de queries (psycopg.Cursor ou sqlite3.Cursor).
        """
        if self.use_sqlite:
            conn = self.get_connection()
            cur = conn.cursor()
            try:
                yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cur.close()
        else:
            conn = self.get_connection()
            try:
                with conn.cursor() as cur:
                    yield cur
                conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                conn.close()

    def execute(self, query: str, params: Tuple[Any, ...] = ()) -> int:
        """
        Executa uma instrução DML (INSERT, UPDATE, DELETE) e confirma a transação.

        Parâmetros:
            query (str): Instrução SQL parametrizada (%s).
            params (Tuple[Any, ...]): Parâmetros a serem interpolados.

        Retorno:
            int: Quantidade de linhas afetadas pela execução.
        """
        sql, normalized_params = self._prepare_query_and_params(query, params)
        with self.session() as cur:
            cur.execute(sql, normalized_params)
            return cur.rowcount if hasattr(cur, "rowcount") else 0

    def fetch_one(self, query: str, params: Tuple[Any, ...] = ()) -> Optional[Dict[str, Any]]:
        """
        Executa uma consulta SELECT e retorna a primeira linha encontrada convertida em dicionário.

        Parâmetros:
            query (str): Instrução SQL de consulta (%s).
            params (Tuple[Any, ...]): Parâmetros da consulta.

        Retorno:
            Optional[Dict[str, Any]]: Dicionário com colunas e valores ou None.
        """
        sql, normalized_params = self._prepare_query_and_params(query, params)
        with self.session() as cur:
            cur.execute(sql, normalized_params)
            row = cur.fetchone()
            if row is None:
                return None
            return dict(row)

    def fetch_all(self, query: str, params: Tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        """
        Executa uma consulta SELECT e retorna todas as linhas encontradas convertidas em dicionários.

        Parâmetros:
            query (str): Instrução SQL de consulta (%s).
            params (Tuple[Any, ...]): Parâmetros da consulta.

        Retorno:
            List[Dict[str, Any]]: Lista de dicionários representando as linhas retornadas.
        """
        sql, normalized_params = self._prepare_query_and_params(query, params)
        with self.session() as cur:
            cur.execute(sql, normalized_params)
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    def execute_schema_sql(self, sql_script: str) -> None:
        """
        Executa um script DDL SQL completo para criação ou atualização de tabelas e índices.

        Trata automaticamente diferenças de sintaxe quando em modo SQLite.

        Parâmetros:
            sql_script (str): Conteúdo textual completo do arquivo SQL DDL.
        """
        if self.use_sqlite:
            conn = self.get_connection()
            sqlite_sql = (
                sql_script
                .replace("UUID PRIMARY KEY DEFAULT gen_random_uuid()", "TEXT PRIMARY KEY")
                .replace("UUID", "TEXT")
                .replace("JSONB", "TEXT")
                .replace("TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP", "DATETIME DEFAULT CURRENT_TIMESTAMP")
                .replace("TIMESTAMP WITH TIME ZONE", "DATETIME")
                .replace("BIGINT", "INTEGER")
                .replace('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";', "")
                .replace("USING GIN", "")
            )
            lines = []
            for line in sqlite_sql.splitlines():
                if "WHERE envelope_status" in line or "WHERE status_envelope" in line:
                    line = line.split("WHERE")[0] + ";"
                if "ALTER TABLE" in line and "ADD COLUMN" in line:
                    continue
                lines.append(line)
            clean_sql = "\n".join(lines)
            conn.executescript(clean_sql)
            conn.commit()
        else:
            with self.session() as cur:
                cur.execute(sql_script)
