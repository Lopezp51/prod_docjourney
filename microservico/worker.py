"""
Módulo de Processamento em Background / Consumidor RabbitMQ (Worker).
Consome mensagens e eventos de filas do RabbitMQ e sincroniza o estado dos envelopes
e histórico de manutenção no banco relacional sem requisições SQL manuais.
"""

import threading
import time
from typing import Dict, Any, Optional, Tuple
from uuid import UUID

from microservico.logging_config import logger
from microservico.api.dependencies import get_db_manager
from microservico.infrastructure.repositories import (
    EnvelopeRepository,
    JourneyRepository,
    MaintenanceHistoryRepository
)
from microservico.domain.enums import EnvelopeStatus, MaintenanceReason
from microservico.notifier.rabbitmq_client import RabbitMQClient



class StatusEventConsumer:
    """
    Consumidor de eventos da fila RabbitMQ.
    Processa mensagens de mudança de status e auditoria, atualizando o banco de dados.
    """

    def __init__(self, rabbitmq_client: RabbitMQClient = None):
        self.db_manager = get_db_manager()
        self.envelope_repo = EnvelopeRepository(self.db_manager)
        self.journey_repo = JourneyRepository(self.db_manager)
        self.maintenance_repo = MaintenanceHistoryRepository(self.db_manager)
        self.rabbitmq = rabbitmq_client or RabbitMQClient(queue_name="docjourney_status_queue")

    def process_message(self, message: Dict[str, Any]) -> bool:
        """
        Processa uma mensagem recebida da fila.

        Tipos de eventos suportados:
        - ENVELOPE_STATUS_UPDATED: Sincroniza o novo status do envelope no banco.
        - ENVELOPE_CANCELED: Marca cancelamento e loga na maintenance_history.
        - ENVELOPE_EXPIRED: Marca expiração do envelope.
        - MAINTENANCE_LOG: Registra ocorrência de intervenção ou erro.
        """
        event_type = message.get("event_type")
        logger.info(f"Processando evento: {event_type} | Payload: {message}")

        try:
            if event_type == "ENVELOPE_STATUS_UPDATED":
                envelope_id = UUID(str(message["envelope_id"]))
                new_status = EnvelopeStatus(message["new_status"])
                self.envelope_repo.update_status(envelope_id, new_status)
                logger.info(f"Envelope {envelope_id} sincronizado com status {new_status.value}.")

            elif event_type == "ENVELOPE_CANCELED":
                envelope_id = UUID(str(message["envelope_id"]))
                self.envelope_repo.update_status(envelope_id, EnvelopeStatus.CANCELED)
                logger.info(f"Envelope {envelope_id} marcado como CANCELED pelo worker.")

            elif event_type == "ENVELOPE_EXPIRED":
                envelope_id = UUID(str(message["envelope_id"]))
                self.envelope_repo.update_status(envelope_id, EnvelopeStatus.EXPIRED)
                logger.info(f"Envelope {envelope_id} marcado como EXPIRED pelo worker.")

            elif event_type == "MAINTENANCE_LOG":
                request_id = UUID(str(message["request_id"])) if message.get("request_id") else None
                envelope_id = UUID(str(message["envelope_id"])) if message.get("envelope_id") else None
                reason = MaintenanceReason(message.get("reason_code", "MANUAL_INTERVENTION"))
                description = message.get("description", "Evento de manutenção recebido da fila.")
                if request_id:
                    self.maintenance_repo.log_maintenance(
                        request_id=request_id,
                        envelope_id=envelope_id,
                        reason_code=reason,
                        detailed_description=description
                    )
                logger.info(f"Ocorrência de manutenção registrada para request {request_id}.")

            return True
        except Exception as e:
            logger.exception(f"Erro ao processar mensagem do RabbitMQ: {e}")
            return False


    def run_polling(
        self,
        interval_seconds: float = 1.0,
        max_iterations: Optional[int] = None,
        stop_event: Optional[threading.Event] = None
    ):
        """
        Executa loop contínuo de polling para processamento de mensagens.
        Pode ser interrompido a qualquer momento ativando o `stop_event`.
        """
        logger.info("--> Worker iniciado. Aguardando mensagens na fila...")
        iterations = 0
        while True:
            if stop_event and stop_event.is_set():
                logger.info("--> [Worker] Sinal de parada recebido. Encerrando worker...")
                break

            try:
                messages = self.rabbitmq.consume_messages(max_messages=10)
                for msg in messages:
                    self.process_message(msg)
            except Exception as exc:
                logger.warning(f"--> [Worker] Falha temporária ao consumir mensagens: {exc}")

            iterations += 1
            if max_iterations and iterations >= max_iterations:
                break

            if stop_event:
                if stop_event.wait(timeout=interval_seconds):
                    logger.info("--> [Worker] Encerrando polling por solicitação do stop_event.")
                    break
            else:
                time.sleep(interval_seconds)


def start_worker_thread(
    interval_seconds: float = 1.0,
    rabbitmq_client: Optional[RabbitMQClient] = None
) -> Tuple[threading.Thread, threading.Event]:
    """
    Inicializa o consumidor RabbitMQ em uma thread paralela em background (daemon thread).
    Retorna a instância da thread e o evento de parada (stop_event) para controle gracioso.
    """
    stop_event = threading.Event()
    consumer = StatusEventConsumer(rabbitmq_client=rabbitmq_client)
    worker_thread = threading.Thread(
        target=consumer.run_polling,
        kwargs={"interval_seconds": interval_seconds, "stop_event": stop_event},
        daemon=True,
        name="RabbitMQEmbeddedWorker"
    )
    worker_thread.start()
    return worker_thread, stop_event


if __name__ == "__main__":
    consumer = StatusEventConsumer()
    consumer.run_polling()
