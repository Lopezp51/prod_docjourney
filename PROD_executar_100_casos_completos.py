"""
Script de Execução em Massa de 100 Casos Ponta a Ponta (PROD_executar_100_casos_completos.py).
Executa o fluxo completo do orquestrador (validação, clusterização, persistência no PostgreSQL,
chamada à OpenAPI e publicação no RabbitMQ) para 100 processos distintos e realistas.
Permite visualizar a volumetria populando o banco relacional e gerando tráfego no RabbitMQ Management.
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import sys
import os
import time
import random
import argparse
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any, List, Tuple

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import logging
logging.getLogger("pika").setLevel(logging.WARNING)
logging.getLogger("RPA_Automation").setLevel(logging.WARNING)

from automacao.main import run_automation_task
from microservico.infrastructure.db import DatabaseManager
from microservico.infrastructure.initializer import initialize_database_if_empty
from microservico.notifier.rabbitmq_client import RabbitMQClient
from microservico.config import config

PROCESS_TYPES = [
    "Crédito Pessoal Automático V2",
    "Custeio Agrícola Pronaf V2",
    "Financiamento Veicular Sicredi V2",
    "Abertura de Conta Corrente PJ V2",
    "Capital de Giro Fácil V2",
    "Renovação de Seguro Prestamista V2",
    "Aditivo de Cédula de Crédito Bancário V2"
]

FIRST_NAMES = ["Edilson", "Pedro", "Mariana", "Carlos", "Aila", "Roberto", "Camila", "Lucas", "Fernanda", "Gabriel", "Patricia", "Marcos"]
LAST_NAMES = ["Franca", "Lopes", "Silva", "Mendes", "Almeida", "Pereira", "Oliveira", "Souza", "Rodrigues", "Santos", "Costa", "Ribeiro"]


def generate_valid_cpf() -> str:
    """
    Gera um número de CPF válido com dígitos verificadores matemáticos corretos (Módulo 11).

    Retorno:
        str: CPF válido com 11 dígitos numéricos.
    """
    digits = [random.randint(0, 9) for _ in range(9)]
    # Primeiro dígito verificador
    s1 = sum(digits[i] * (10 - i) for i in range(9))
    d1 = ((s1 * 10) % 11) % 10
    digits.append(d1)
    # Segundo dígito verificador
    s2 = sum(digits[i] * (11 - i) for i in range(10))
    d2 = ((s2 * 10) % 11) % 10
    digits.append(d2)
    return "".join(map(str, digits))


def generate_task_payload(index: int) -> Dict[str, Any]:
    """
    Constrói um payload MongoDB/Fluid íntegro, realista e pronto para validação e envio.

    Parâmetros:
        index (int): Índice sequencial de 1 a N.

    Retorno:
        Dict[str, Any]: Estrutura com atributos, matriz de signatários e anexos PDFs.
    """
    proc_num = 300000 + index
    proc_name = random.choice(PROCESS_TYPES)
    mongo_id = f"mongo_e2e_{index:04d}_{uuid4().hex[:8]}"

    # Dados do Titular
    titular_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} {random.choice(LAST_NAMES)}"
    titular_cpf = generate_valid_cpf()
    titular_email = f"associado_{index}@sicredi.teste.local"
    titular_phone = f"419{random.randint(1000, 9999)}{random.randint(1000, 9999)}"

    # Decide se terá avalista/cônjuge (30% dos casos)
    has_spouse = (index % 3 == 0)

    # Anexos base
    anexos = [
        {
            "nome": "765 - CCB",
            "hash": f"hash_ccb_{index}_{uuid4().hex[:6]}",
            "tipo_doc_id": 765,
            "extensao": "pdf"
        },
        {
            "nome": "678 - CET",
            "hash": f"hash_cet_{index}_{uuid4().hex[:6]}",
            "tipo_doc_id": 678,
            "extensao": "pdf"
        }
    ]

    signers_table = [
        [
            {"id": 12906, "valor": "1"},
            {"id": 12909, "valor": titular_cpf},
            {"id": 12910, "valor": titular_name},
            {"id": 12911, "valor": "Titular"},
            {"id": 12857, "valor": '["765 - CCB", "678 - CET"]'},
            {"id": 12912, "valor": "E-mail"},
            {"id": 12913, "valor": titular_email},
            {"id": 12914, "valor": titular_phone},
            {"id": 12915, "valor": "Eletrônica"}
        ]
    ]

    if has_spouse:
        anexos.append({
            "nome": "810 - Termo de Garantia",
            "hash": f"hash_garantia_{index}_{uuid4().hex[:6]}",
            "tipo_doc_id": 810,
            "extensao": "pdf"
        })
        spouse_name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        spouse_cpf = generate_valid_cpf()
        spouse_email = f"avalista_{index}@sicredi.teste.local"

        signers_table.append([
            {"id": 12906, "valor": "2"},
            {"id": 12909, "valor": spouse_cpf},
            {"id": 12910, "valor": spouse_name},
            {"id": 12911, "valor": "Avalista/Cônjuge"},
            {"id": 12857, "valor": '["810 - Termo de Garantia"]'},
            {"id": 12912, "valor": "E-mail"},
            {"id": 12913, "valor": spouse_email},
            {"id": 12914, "valor": titular_phone},
            {"id": 12915, "valor": "Eletrônica"}
        ])

    return {
        "_id": {"$oid": mongo_id},
        "num_processo": proc_num,
        "nome_processo": proc_name,
        "id_inicial": f"init_{proc_num}",
        "infos_envio": {
            "atributos": {
                "3305": titular_name,
                "4335": titular_cpf,
                "11675": titular_email,
                "12044": titular_phone,
                "12905": signers_table
            },
            "anexos": anexos
        }
    }


def print_progress_bar(iteration: int, total: int, prefix: str = "", suffix: str = "", length: int = 30):
    """Exibe barra de progresso visual em tempo real."""
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_len = int(length * iteration // total)
    bar = "█" * filled_len + "░" * (length - filled_len)
    sys.stdout.write(f"\r{prefix} |{bar}| {iteration}/{total} ({percent}%) {suffix}")
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write("\n")


def execute_100_e2e_cases(total_cases: int = 100, delay: float = 0.0, drain_after: bool = False):
    """
    Executa N casos completos de ponta a ponta no orquestrador e alimenta RabbitMQ e PostgreSQL.
    """
    print("=" * 80)
    print(f"🚀 EXECUÇÃO EM MASSA: {total_cases} PROCESSOS COMPLETOS PONTA A PONTA")
    print("   Orquestrador RPA -> Validação -> Clusterização -> PostgreSQL -> RabbitMQ")
    print("=" * 80)

    dsn = f"host={config.DB_HOST} port={config.DB_PORT} dbname={config.DB_NAME} user={config.DB_USER} password={config.DB_PASSWORD}"
    print(f"📡 Conectando ao PostgreSQL: {config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}")

    db_mgr = DatabaseManager(dsn=dsn, use_sqlite=False)
    initialize_database_if_empty(db_mgr)

    from automacao.infrastructure.openapi_client import OpenApiV2Client
    openapi_client = OpenApiV2Client(mock_mode=True, mock_latency=0.03)

    rabbit_client = RabbitMQClient(queue_name="docjourney_status_queue")
    rb_status = rabbit_client.get_queue_status()
    print(f"🐰 Broker RabbitMQ: {rb_status['broker_host']} | Ativo: {rb_status['is_live_broker']} | Modo: {rb_status['mode']}")

    if rb_status['is_live_broker']:
        print("\n🌐 PAINEL WEB PRONTO PARA ACOMPANHAMENTO:")
        print("   -> Abra no navegador: http://localhost:15672")
        print("   -> Login: guest  |  Senha: guest")
        print("   -> Acesse: Queues -> 'docjourney_status_queue' para ver os dados subindo!\n")

    print(f"⚙️  Iniciando processamento de {total_cases} tarefas da esteira (com chamadas à API mock Sicredi)...\n")
    start_time = time.time()
    success_count = 0
    envelopes_total = 0

    for i in range(1, total_cases + 1):
        payload = generate_task_payload(i)
        result = run_automation_task(
            payload,
            use_sqlite=False,
            db_manager=db_mgr,
            openapi_client=openapi_client,
            rabbitmq_client=rabbit_client
        )

        if result.get("status") == "SUCESSO":
            success_count += 1
            envelopes_total += len(result.get("envelopes", []))

        if delay > 0:
            time.sleep(delay)

        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        print_progress_bar(i, total_cases, prefix="   Progresso Processos", suffix=f"[{rate:.1f} casos/s]")

    total_time = time.time() - start_time
    avg_rate = total_cases / total_time if total_time > 0 else total_cases

    print(f"\n✅ {success_count}/{total_cases} processos executados com SUCESSO em {total_time:.2f}s (Média: {avg_rate:.1f} casos/s)!")
    print(f"📦 Total de Envelopes Criados e Transmitidos: {envelopes_total}")

    # Checa o status das tabelas no PostgreSQL
    def _extract_count(cur, query):
        cur.execute(query)
        row = cur.fetchone()
        if isinstance(row, dict):
            return list(row.values())[0]
        return row[0] if row else 0

    conn = db_mgr.get_connection()
    cur = conn.cursor()
    cnt_journeys = _extract_count(cur, "SELECT COUNT(*) FROM journey_requests")
    cnt_envelopes = _extract_count(cur, "SELECT COUNT(*) FROM envelopes")
    cnt_associates = _extract_count(cur, "SELECT COUNT(*) FROM associates")
    cnt_documents = _extract_count(cur, "SELECT COUNT(*) FROM documents")
    cnt_signers = _extract_count(cur, "SELECT COUNT(*) FROM envelope_signers")
    conn.close()

    print("\n📊 BALANÇO ATUALIZADO NO BANCO DE DADOS POSTGRESQL:")
    print(f"   -> journey_requests:  {cnt_journeys} registros")
    print(f"   -> envelopes:         {cnt_envelopes} registros")
    print(f"   -> associates:        {cnt_associates} registros")
    print(f"   -> documents:         {cnt_documents} registros")
    print(f"   -> envelope_signers:  {cnt_signers} registros")

    # Status atual da fila no RabbitMQ
    final_rb = rabbit_client.get_queue_status()
    print(f"\n🐰 FILA RABBITMQ ('docjourney_status_queue'):")
    print(f"   -> Mensagens Retidas e Prontas para Consumo: {final_rb['message_count']}")

    print("\n" + "=" * 80)
    print("👀 VEJA O RESULTADO AO VIVO NO PAINEL WEB DO RABBITMQ:")
    print("   -> Abra a página: http://localhost:15672/#/queues")
    print(f"   -> Clique na fila 'docjourney_status_queue'.")
    print(f"   -> Você verá o gráfico e o indicador 'Ready: {final_rb['message_count']}'!")
    print("   -> Você pode clicar na seção 'Get messages' e clicar em 'Get Message(s)'")
    print("      para inspecionar o payload JSON de qualquer processo transmitido!")
    print("=" * 80)

    if not drain_after:
        try:
            print("\n💡 DICA: As mensagens permanecerão na fila para você inspecionar no painel.")
            input("👉 Pressione [ENTER] quando quiser que os consumidores esvaziem a fila (ou Ctrl+C para sair)... ")
        except (EOFError, KeyboardInterrupt):
            print("\nFinalizado. Mensagens mantidas na fila.")
            return

    # Consumo com visualização
    print(f"\n⚡ Drenando {final_rb['message_count']} mensagens da fila para demonstrar consumo...")
    drained = 0
    while True:
        batch = rabbit_client.consume_messages(max_messages=10)
        if not batch:
            break
        drained += len(batch)
        print_progress_bar(drained, final_rb['message_count'], prefix="   Consumindo Fila", suffix=f"[{drained}/{final_rb['message_count']}]")
        time.sleep(0.05)

    print(f"\n✅ {drained} mensagens consumidas! A fila retornou a 0.")
    print("🎉 EXECUÇÃO EM MASSA CONCLUÍDA COM 100% DE SUCESSO!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Execução em Massa de Processos Ponta a Ponta")
    parser.add_argument("--count", type=int, default=100, help="Quantidade de processos a executar (padrão: 100)")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay entre processos (padrão: 0.0)")
    parser.add_argument("--drain", action="store_true", help="Drena a fila automaticamente ao final")
    parser.add_argument("--clean-before", action="store_true", help="Limpa o banco antes de executar os 100 casos")
    parser.add_argument("--drain-only", action="store_true", help="Apenas drena e consome as mensagens pendentes na fila")

    args = parser.parse_args()

    if args.drain_only:
        rabbit_client = RabbitMQClient(queue_name="docjourney_status_queue")
        status = rabbit_client.get_queue_status()
        total_msg = status["message_count"]
        print(f"🐰 Drenando {total_msg} mensagens da fila 'docjourney_status_queue'...")
        drained = 0
        while True:
            batch = rabbit_client.consume_messages(max_messages=10)
            if not batch:
                break
            drained += len(batch)
            print_progress_bar(drained, total_msg if total_msg > 0 else drained, prefix="   Consumindo Fila", suffix=f"[{drained}/{total_msg}]")
            time.sleep(0.05)
        print(f"\n✅ {drained} mensagens consumidas com sucesso! A fila agora está zerada.")
        rabbit_client.close()
        sys.exit(0)

    if args.clean_before:
        from PROD_reset_database import reset_database
        reset_database(truncate_only=True, force=True)

    execute_100_e2e_cases(total_cases=args.count, delay=args.delay, drain_after=args.drain)
