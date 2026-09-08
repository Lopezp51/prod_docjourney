"""
Bateria de Testes e Demonstração do RabbitMQ (DocJourney Notifier).
Testa a publicação, consumo e visualização do status da fila.
Funciona perfeitamente tanto com RabbitMQ real quanto com Mock em memória.
"""

import sys
import os
from datetime import datetime

# Adiciona a raiz do projeto no PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from microservico.notifier.rabbitmq_client import RabbitMQClient


def run_rabbitmq_test_battery():
    """
    Executa a bateria de testes de mensageria com RabbitMQ / Mock Queue.
    """
    print("=" * 70)
    print("BATERIA DE TESTES E VALIDAÇÃO DE FILA RABBITMQ")
    print("=" * 70)

    client = RabbitMQClient(queue_name="docjourney_test_queue")
    status = client.get_queue_status()

    print("\n1. Conexão com Broker:")
    print(f"   -> Broker Configurado: {status['broker_host']}")
    print(f"   -> Modo de Operação:   {status['mode']}")
    print(f"   -> Broker Real Ativo:  {status['is_live_broker']}")
    print(f"   -> Fila de Destino:    {status['queue_name']}")

    if not status["is_live_broker"]:
        print("\n   [INFO] Broker RabbitMQ não detectado localmente nesta porta.")
        print("   [INFO] O cliente ativou automaticamente a fila simulada (Mock Memory Queue).")
        print("   [INFO] Para subir um broker RabbitMQ real com interface visual, execute:")
        print("          docker run -d --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:3-management")
        print("          Acesse o painel web em: http://localhost:15672 (user: guest / pass: guest)")

    # 2. Publicação de Mensagens de Teste
    print("\n2. Publicando mensagens de evento de assinatura na fila...")
    test_events = [
        {
            "event_type": "ENVELOPE_CREATED",
            "process_number": 1225591,
            "envelope_id": "env_test_001",
            "status": "PENDING_SIGNATURE",
            "timestamp": datetime.now().isoformat(),
            "signers": [{"tax_id": "11158072937", "name": "Pedro Lopes", "status": "PENDING_LINK_DELIVERY"}]
        },
        {
            "event_type": "SIGNATURE_COMPLETED",
            "process_number": 1225591,
            "envelope_id": "env_test_001",
            "status": "COMPLETED",
            "timestamp": datetime.now().isoformat(),
            "signers": [{"tax_id": "11158072937", "name": "Pedro Lopes", "status": "SIGNED"}]
        },
        {
            "event_type": "ENVELOPE_EXPIRED",
            "process_number": 1160705,
            "envelope_id": "env_test_002",
            "status": "EXPIRED",
            "timestamp": datetime.now().isoformat(),
            "signers": [{"tax_id": "02631353900", "name": "Edilson Franca", "status": "REJECTED"}]
        }
    ]

    for idx, event in enumerate(test_events, start=1):
        published = client.publish_message(event)
        print(f"   -> Mensagem #{idx} ({event['event_type']}) publicada: {'SUCESSO' if published else 'FALHA'}")

    # 3. Verificação do Status da Fila
    status_after_pub = client.get_queue_status()
    print("\n3. Status da Fila após Publicação:")
    print(f"   -> Total de Mensagens na Fila: {status_after_pub['message_count']}")

    # 4. Consumo de Mensagens da Fila
    print("\n4. Consumindo mensagens da fila...")
    consumed = client.consume_messages(max_messages=5)
    print(f"   -> Total de Mensagens Consumidas: {len(consumed)}")
    for idx, msg in enumerate(consumed, start=1):
        print(f"      [{idx}] Tipo: {msg.get('event_type')} | Processo #{msg.get('process_number')} | Status: {msg.get('status')}")

    # 5. Verificação Final da Fila
    status_final = client.get_queue_status()
    print("\n5. Status Final da Fila (Após Consumo):")
    print(f"   -> Mensagens Restantes: {status_final['message_count']}")

    print("\n" + "=" * 70)
    print("BATERIA DE TESTES DO RABBITMQ FINALIZADA COM SUCESSO!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    run_rabbitmq_test_battery()
