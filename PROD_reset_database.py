"""
Script Utilitário para Reset e Limpeza do Banco de Dados Relacional (PROD_reset_database.py).
Permite zerar os dados de homologação/teste ou recriar completamente a estrutura do PostgreSQL.

Opções disponíveis via linha de comando:
  --clean / --truncate : Limpa todas as tabelas transacionais preservando o catálogo de processos.
  --recreate / --drop  : Exclui e recria do zero todas as tabelas via PROD_schema.sql (padrão).
  --seed               : Após resetar, popula automaticamente com a massa de dados de teste.
  --force / -y         : Pula a solicitação de confirmação interativa.

Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import os
import sys
import argparse

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.config import config


DROP_TABLES_SQL = """
DROP TABLE IF EXISTS maintenance_history CASCADE;
DROP TABLE IF EXISTS envelope_signers CASCADE;
DROP TABLE IF EXISTS documents CASCADE;
DROP TABLE IF EXISTS envelopes CASCADE;
DROP TABLE IF EXISTS journey_requests CASCADE;
DROP TABLE IF EXISTS process_configurations CASCADE;
DROP TABLE IF EXISTS processes CASCADE;
DROP TABLE IF EXISTS associates CASCADE;
"""

TRUNCATE_TABLES_SQL = """
TRUNCATE TABLE 
    maintenance_history,
    envelope_signers,
    documents,
    envelopes,
    journey_requests,
    associates
CASCADE;
"""


def get_table_counts(conn, use_sqlite: bool = False):
    """
    Retorna a contagem atual de registros em cada uma das tabelas do sistema.

    Parâmetros:
        conn: Objeto de conexão ativa com o banco.
        use_sqlite (bool): Indica se é SQLite ou PostgreSQL.

    Retorno:
        dict: Mapeamento de nome_da_tabela -> total_de_registros.
    """
    tables = [
        "associates",
        "processes",
        "process_configurations",
        "journey_requests",
        "envelopes",
        "documents",
        "envelope_signers",
        "maintenance_history"
    ]
    counts = {}
    cur = conn.cursor()
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            row = cur.fetchone()
            counts[table] = row[0] if isinstance(row, (list, tuple)) else row.get("count", 0)
        except Exception:
            counts[table] = "N/A"
    if not use_sqlite:
        conn.commit()
    return counts


def reset_database(
    recreate: bool = True,
    truncate_only: bool = False,
    seed_after: bool = False,
    force: bool = False
) -> bool:
    """
    Executa o procedimento de limpeza ou recriação do banco de dados relacional.

    Parâmetros:
        recreate (bool): Se True, executa DROP CASCADE e recria via PROD_schema.sql.
        truncate_only (bool): Se True, apenas trunca tabelas mantendo o catálogo.
        seed_after (bool): Se True, executa a carga de dados de teste após resetar.
        force (bool): Se True, não solicita confirmação no terminal.

    Retorno:
        bool: True se o reset foi executado com sucesso.
    """
    print("=" * 80)
    print("🧹 UTILITÁRIO DE LIMPEZA E RESET DO BANCO DE DADOS (DOCJOURNEY)")
    print("=" * 80)

    dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
    print(f"📡 Banco Alvo: PostgreSQL em {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME} (Usuário: {config.DB_USER})")

    # Solicitação de Confirmação Interativa
    if not force:
        action_desc = "TRUNCAR todos os dados transacionais" if truncate_only else "RECRIAR do zero todas as tabelas (DROP CASCADE)"
        print(f"\n⚠️  ATENÇÃO: Você está prestes a {action_desc} no banco '{config.DB_NAME}'.")
        print("   Todos os testes anteriores e dados de histórico serão apagados permanentemente.")
        try:
            confirm = input("\n👉 Deseja realmente prosseguir? Digite 'sim' ou 's' para confirmar: ").strip().lower()
            if confirm not in ("s", "sim", "y", "yes"):
                print("\n❌ Operação cancelada pelo usuário. O banco permanece inalterado.")
                return False
        except EOFError:
            pass

    db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)
    conn = db_mgr.get_connection()

    try:
        if truncate_only:
            print("\n🗑️  Truncando tabelas transacionais (associates, journeys, envelopes, documents, signers, maintenance)...")
            with conn.cursor() as cur:
                cur.execute(TRUNCATE_TABLES_SQL)
            conn.commit()
            print("✅ Tabelas transacionais limpas com sucesso!")
        else:
            print("\n🔥 Executando DROP CASCADE em todas as tabelas...")
            with conn.cursor() as cur:
                cur.execute(DROP_TABLES_SQL)
            conn.commit()

            print("🏗️  Recriando estrutura completa via PROD_schema.sql...")
            initialize_database_if_empty(db_mgr)
            print("✅ Esquema PROD_schema.sql e catálogo base recriados com sucesso!")

        # Opcional: Popula com dados de teste
        if seed_after:
            print("\n🌱 Populando banco com dados de exemplo (PROD_populate_sample_data)...")
            from PROD_populate_sample_data import populate_sample_data
            populate_sample_data()

        # Exibe o balanço de registros atualizado
        print("\n📊 BALANÇO ATUAL DE REGISTROS NO BANCO:")
        counts = get_table_counts(conn, use_sqlite=False)
        for tbl, cnt in counts.items():
            print(f"   -> {tbl:<25}: {cnt} registros")

        print("\n" + "=" * 80)
        print("🎉 OPERAÇÃO DE RESET CONCLUÍDA COM SUCESSO!")
        print("   O ambiente está 100% pronto para nova rodada de testes e homologação.")
        print("=" * 80)
        return True

    except Exception as err:
        conn.rollback()
        print(f"\n❌ Erro durante o reset do banco de dados: {err}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Utilitário de Reset do Banco de Dados DocJourney")
    parser.add_argument(
        "--clean", "--truncate",
        action="store_true",
        help="Apenas limpa os dados das tabelas transacionais, mantendo o catálogo"
    )
    parser.add_argument(
        "--recreate", "--drop",
        action="store_true",
        help="Exclui (DROP) e recria todas as tabelas via PROD_schema.sql (padrão)"
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Após o reset, popula automaticamente com a massa de dados de teste"
    )
    parser.add_argument(
        "-y", "--yes", "--force",
        action="store_true",
        help="Pula a confirmação interativa no terminal"
    )

    args = parser.parse_args()
    truncate_flag = args.clean
    recreate_flag = not truncate_flag

    reset_database(
        recreate=recreate_flag,
        truncate_only=truncate_flag,
        seed_after=args.seed,
        force=args.yes or args.force
    )
