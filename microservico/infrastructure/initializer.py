"""
Módulo de Inicialização e Carga de Dados Básicos (Seed Data) do Banco de Dados.
Garante que as tabelas necessárias e os processos catalogados estejam disponíveis.
Código 100% em inglês com docstrings em português.
"""

import os
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.repositories import ProcessRepository

# Busca primeiramente o PROD_schema.sql na raiz do projeto, com fallback para schema.sql
PROD_SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "PROD_schema.sql"))
FALLBACK_SCHEMA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "schema.sql"))


def initialize_database_if_empty(db_manager: DatabaseManager) -> None:
    """
    Verifica e inicializa o banco de dados (PostgreSQL ou SQLite) de forma idempotente.

    Passos executados:
    1. Localiza e executa o script DDL SQL (PROD_schema.sql) com CREATE TABLE IF NOT EXISTS.
    2. Popula os processos essenciais de negócio (Seed Data) caso ainda não existam.

    Parâmetros:
        db_manager (DatabaseManager): Instância do gerenciador de conexões com o banco.
    """
    schema_path = PROD_SCHEMA_PATH if os.path.exists(PROD_SCHEMA_PATH) else FALLBACK_SCHEMA_PATH

    if os.path.exists(schema_path):
        with open(schema_path, "r", encoding="utf-8") as schema_file:
            schema_sql = schema_file.read()
        db_manager.execute_schema_sql(schema_sql)

    # Carga Inicial de Processos Homologados da Esteira Sicredi (Seed Data)
    process_repo = ProcessRepository(db_manager)

    initial_processes = [
        {
            "name": "Solicitação de Crédito Comercial V2",
            "description": "Processo de concessão e renovação de crédito comercial para associados"
        },
        {
            "name": "Renovação Seguros V2",
            "description": "Processo de contratação e renovação de apólices de seguro patrimonial e de vida"
        },
        {
            "name": "Abertura de Conta V2",
            "description": "Processo de cadastro de associados e abertura de conta corrente cooperativa"
        }
    ]

    for item in initial_processes:
        process_repo.get_or_create(name=item["name"], description=item["description"])


if __name__ == "__main__":
    db_mgr = DatabaseManager(use_sqlite=True)
    initialize_database_if_empty(db_mgr)
    print("Database initialized and seed processes created successfully!")
