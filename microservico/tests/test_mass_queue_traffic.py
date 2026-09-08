"""
Simulador de Carga e Tráfego em Massa para Mensageria RabbitMQ (DocJourney Traffic Engine).
Permite visualizar a publicação e consumo em lote ou streaming contínuo de centenas/milhares de mensagens.
Projetado para acompanhamento visual no console e no painel web do RabbitMQ (http://localhost:15672).
Nomes de classes, métodos e variáveis em inglês com docstrings explicativas em português.
"""

import sys
import os
import time
import random
import argparse
from datetime import datetime
from uuid import uuid4
from typing import Dict, Any

# Adiciona raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.notifier.rabbitmq_client import RabbitMQClient

EVENT_TYPES = [
    ("ENVELOPE_CREATED", "PENDING_SIGNATURE"),
    ("SIGNATURE_COMPLETED", "COMPLETED"),
    ("SELECTIVE_REPLACEMENT", "REPLACED_CANCELED"),
    ("ENVELOPE_EXPIRED", "EXPIRED"),
    ("DOCUMENT_ATTACHED", "WAITING_SIGNATURE")
]

PROCESS_NAMES = [
    "Crédito Pessoal Automático",
    "Custeio Agro Safra 2026",
    "Abertura de Conta Corrente PJ",
    "Financiamento de Energia Solar",
    "Aditivo de Cédula de Crédito Bancário",
    "Termo de Renegociação de Dívida"
]

SAMPLE_SIGNERS = [
    ("02631353900", "Edilson Paulo de Franca"),
    ("11158072937", "Aila Elo de Franca"),
    ("08489951985", "Pedro Henrique Lopes"),
    ("52998224725", "Mariana Silva de Souza"),
    ("70339281057", "Carlos Eduardo Mendes")
]


def generate_mock_event(index: int) -> Dict[str, Any]:
    """
    Gera um payload JSON realista de evento de assinatura para simulação de volumetria.

    Parâmetros:
        index (int): Índice sequencial da mensagem.

    Retorno:
        Dict[str, Any]: Dicionário com payload formatado.
    """
    event_type, status = random.choice(EVENT_TYPES)
    process_name = random.choice(PROCESS_NAMES)
    signer_cpf, signer_name = random.choice(SAMPLE_SIGNERS)

    return {
        "event_id": f"evt_{uuid4().hex[:12]}",
        "event_type": event_type,
        "sequence_number": index,
        "process_number": 200000 + (index % 1000),
        "process_name": process_name,
        "envelope_id": f"env_{uuid4().hex[:8]}",
        "envelope_status": status,
        "timestamp": datetime.now().isoformat(),
        "origin_system": "DOCJOURNEY_ORCHESTRATOR",
        "signers": [
            {
                "tax_id": signer_cpf,
                "name": signer_name,
                "status": "SIGNED" if status == "COMPLETED" else "PENDING_LINK_DELIVERY"
            }
        ]
    }


def print_progress_bar(iteration: int, total: int, prefix: str = "", suffix: str = "", length: int = 30):
    """
    Exibe barra de progresso gráfica interativa no console.
    """
    percent = f"{100 * (iteration / float(total)):.1f}"
    filled_len = int(length * iteration // total)
    bar = "█" * filled_len + "░" * (length - filled_len)
    sys.stdout.write(f"\r{prefix} |{bar}| {iteration}/{total} ({percent}%) {suffix}")
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write("\n")


def run_mass_simulation(
    count: int = 50,
    delay: float = 0.0,
    queue_name: str = "docjourney_status_queue",
    interactive_pause: bool = True
):
    """
    Executa o teste de carga e acompanhamento em tempo real da fila.

    Parâmetros:
        count (int): Quantidade de mensagens para disparar em lote.
        delay (float): Delay em segundos entre mensagens (ex: 0.1 para streaming visual).
        queue_name (str): Nome da fila do RabbitMQ.
        interactive_pause (bool): Se True, aguarda o usuário conferir a fila no navegador antes de consumir.
    """
    print("=" * 80)
    print("🚀 SIMULADOR DE CARGA E MONITORAMENTO EM MASSA - RABBITMQ")
    print("=" * 80)

    client = RabbitMQClient(queue_name=queue_name)
    initial_status = client.get_queue_status()

    print("\n📡 ESTADO DA CONEXÃO COM O BROKER:")
    print(f"   -> Host / Porta:       {initial_status['broker_host']}")
    print(f"   -> Fila Alvo:          {queue_name}")
    print(f"   -> Modo Operacional:   {initial_status['mode']}")
    print(f"   -> Broker Real Ativo:  {initial_status['is_live_broker']}")
    print(f"   -> Mensagens Atuais:   {initial_status['message_count']}")

    if initial_status["is_live_broker"]:
        print("\n   🌐 PAINEL WEB DISPONÍVEL:")
        print("      Abra no navegador: http://localhost:15672")
        print("      Login: guest  |  Senha: guest")
        print("      Navegue até a aba 'Queues' -> clique em 'docjourney_status_queue'")
        print("      Você verá as mensagens chegando e o gráfico subindo em tempo real!\n")
    else:
        print("\n   ⚠️ [AVISO] RabbitMQ real não detectado nesta porta.")
        print("      Operando no modo MOCK_MEMORY ultra-rápido em memória local.\n")

    # 1. FASE DE ENVIO EM MASSA (PUBLISH)
    print(f"📦 [FASE 1] Publicando {count} mensagens na fila...")
    start_publish_time = time.time()

    for i in range(1, count + 1):
        event = generate_mock_event(i)
        client.publish_message(event)

        if delay > 0:
            time.sleep(delay)

        elapsed = time.time() - start_publish_time
        rate = i / elapsed if elapsed > 0 else 0
        print_progress_bar(i, count, prefix="   Progresso Envio", suffix=f"[{rate:.1f} msg/s]")

    total_pub_time = time.time() - start_publish_time
    avg_pub_rate = count / total_pub_time if total_pub_time > 0 else count

    print(f"\n✅ {count} mensagens publicadas com sucesso em {total_pub_time:.2f}s (Média: {avg_pub_rate:.1f} msg/s)!")

    # 2. STATUS APÓS CARGA
    mid_status = client.get_queue_status()
    print(f"\n📊 [STATUS DA FILA]: {mid_status['message_count']} mensagens prontas para consumo.")

    # 3. PAUSA PARA OBSERVAÇÃO VISUAL NO NAVEGADOR
    if interactive_pause:
        print("\n" + "-" * 80)
        print("👀 OBSERVAÇÃO NO PAINEL WEB:")
        print(f"   -> As {count} mensagens estão retidas na fila '{queue_name}'.")
        print("   -> Você pode abrir http://localhost:15672 para ver o contador cheio!")
        print("-" * 80)
        try:
            input("   👉 Pressione [ENTER] para acionar os consumidores e esvaziar a fila...")
        except EOFError:
            pass

    # 4. FASE DE CONSUMO EM MASSA (CONSUME)
    print("\n⚡ [FASE 2] Consumindo e processando mensagens da fila...")
    start_consume_time = time.time()
    consumed_total = 0

    batch_size = 10
    while True:
        batch = client.consume_messages(max_messages=batch_size)
        if not batch:
            break
        consumed_total += len(batch)
        print_progress_bar(consumed_total, count, prefix="   Progresso Consumo", suffix=f"[{consumed_total}/{count}]")
        if delay > 0:
            time.sleep(delay / 2)

    total_cons_time = time.time() - start_consume_time
    avg_cons_rate = consumed_total / total_cons_time if total_cons_time > 0 else consumed_total

    print(f"\n✅ {consumed_total} mensagens consumidas e confirmadas em {total_cons_time:.2f}s (Média: {avg_cons_rate:.1f} msg/s)!")

    # 5. STATUS FINAL
    final_status = client.get_queue_status()
    print(f"\n🎯 [STATUS FINAL]: {final_status['message_count']} mensagens restantes na fila.")
    print("=" * 80)
    print("🎉 SIMULAÇÃO EM MASSA CONCLUÍDA COM 100% DE SUCESSO!")
    print("=" * 80)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulador de Carga em Massa RabbitMQ")
    parser.add_argument("--count", type=int, default=50, help="Quantidade de mensagens a publicar (padrão: 50)")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay em segundos entre publicações (ex: 0.1 para streaming visual)")
    parser.add_argument("--queue", type=str, default="docjourney_status_queue", help="Nome da fila de teste")
    parser.add_argument("--no-pause", action="store_true", help="Não pausa antes de consumir (execução direta)")

    args = parser.parse_args()
    run_mass_simulation(
        count=args.count,
        delay=args.delay,
        queue_name=args.queue,
        interactive_pause=not args.no_pause
    )
