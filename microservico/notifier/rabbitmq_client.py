"""
Módulo de Integração com Mensageria RabbitMQ.
Fornece cliente resiliente para publicação e consumo de eventos de envelopes e signatários.
Suporta conexão com broker real (AMQP) e fallback transparente para fila em memória (modo Mock).
Nomes de classes, métodos e variáveis 100% em inglês com docstrings explicativas em português.
"""

import json
from typing import Dict, Any, Optional, List

try:
    import pika
except ImportError:
    pika = None

from microservico.logging_config import logger
from microservico.config import config



class RabbitMQClient:
    """
    Cliente de mensageria RabbitMQ com alta resiliência para produção e homologação.

    Caso o broker RabbitMQ não esteja acessível no host/porta configurados,
    o cliente opera em modo de emulação (Mock Queue), permitindo que fluxos de testes
    e validações locais ocorram sem interrupções.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        queue_name: str = "docjourney_status_queue"
    ):
        """
        Inicializa o cliente RabbitMQ com parâmetros de conexão.

        Parâmetros:
            host (Optional[str]): Endereço do host do RabbitMQ (padrão: config.RABBITMQ_HOST).
            port (Optional[int]): Porta AMQP do broker (padrão: config.RABBITMQ_PORT).
            user (Optional[str]): Usuário de autenticação (padrão: config.RABBITMQ_USER).
            password (Optional[str]): Senha de autenticação (padrão: config.RABBITMQ_PASSWORD).
            queue_name (str): Nome da fila principal de destino e escuta.
        """
        self.host = host or config.RABBITMQ_HOST
        self.port = port or config.RABBITMQ_PORT
        self.user = user or config.RABBITMQ_USER
        self.password = password or config.RABBITMQ_PASSWORD
        self.queue_name = queue_name

        self._mock_queue: List[Dict[str, Any]] = []
        self._is_live_connection: bool = False
        self._connection: Optional[Any] = None
        self._channel: Optional[Any] = None
        self._check_connection()

    def _get_channel(self) -> Optional[Any]:
        """
        Retorna ou cria um canal ativo reutilizável na conexão persistente AMQP.

        Retorno:
            Optional[Any]: Canal pika ativo ou None se indisponível.
        """
        if pika is None:
            self._is_live_connection = False
            return None

        if self._connection and not self._connection.is_closed:
            if self._channel and not self._channel.is_closed:
                return self._channel

        try:
            credentials = pika.PlainCredentials(self.user, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                connection_attempts=1,
                retry_delay=0.5,
                socket_timeout=1
            )
            self._connection = pika.BlockingConnection(parameters)
            self._channel = self._connection.channel()
            self._channel.queue_declare(queue=self.queue_name, durable=True)
            self._is_live_connection = True
            return self._channel
        except Exception as err:
            logger.info(f"Broker RabbitMQ offline no host {self.host}:{self.port}. Operando em modo Mock Queue em memória.")
            self._is_live_connection = False
            self._connection = None
            self._channel = None
            return None

    def _check_connection(self) -> bool:
        """
        Verifica se o broker RabbitMQ está acessível via conexão AMQP de teste.

        Retorno:
            bool: True se conectado ao broker real, False se operando em modo Mock.
        """
        channel = self._get_channel()
        return channel is not None

    @property
    def is_live(self) -> bool:
        """
        Indica se o cliente está conectado ao servidor RabbitMQ real ou operando em Mock.

        Retorno:
            bool: True se broker real ativo, False se em Mock.
        """
        return self._is_live_connection

    def publish_message(self, message: Dict[str, Any]) -> bool:
        """
        Publica uma mensagem em formato JSON na fila configurada.

        Parâmetros:
            message (Dict[str, Any]): Dicionário com o payload a ser serializado e publicado.

        Retorno:
            bool: True se a mensagem foi publicada com sucesso (no broker ou mock queue).
        """
        body_bytes = json.dumps(message).encode("utf-8")

        if self._is_live_connection:
            try:
                channel = self._get_channel()
                if channel is not None:
                    channel.basic_publish(
                        exchange="",
                        routing_key=self.queue_name,
                        body=body_bytes,
                        properties=pika.BasicProperties(delivery_mode=2)  # Mensagem persistente
                    )
                    return True
            except Exception as err:
                logger.warning(f"Falha ao publicar no RabbitMQ real ({err}). Alternando para Mock Queue.")
                self._is_live_connection = False
                self._connection = None
                self._channel = None

        # Armazena na fila em memória (Modo Mock)
        self._mock_queue.append(message)
        return True

    def close(self) -> None:
        """Encerra a conexão persistente e canal AMQP com o RabbitMQ."""
        try:
            if self._channel and not self._channel.is_closed:
                self._channel.close()
        except Exception:
            pass
        try:
            if self._connection and not self._connection.is_closed:
                self._connection.close()
        except Exception:
            pass
        self._connection = None
        self._channel = None

    def consume_messages(self, max_messages: int = 10) -> List[Dict[str, Any]]:
        """
        Consome até 'max_messages' mensagens disponíveis na fila configurada.

        Parâmetros:
            max_messages (int): Quantidade máxima de mensagens a recuperar nesta chamada.

        Retorno:
            List[Dict[str, Any]]: Lista de mensagens deserializadas da fila.
        """
        messages_received = []

        if self._is_live_connection:
            try:
                credentials = pika.PlainCredentials(self.user, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    socket_timeout=5
                )
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                channel.queue_declare(queue=self.queue_name, durable=True)

                for _ in range(max_messages):
                    method_frame, header_frame, body = channel.basic_get(queue=self.queue_name, auto_ack=True)
                    if method_frame:
                        try:
                            msg_dict = json.loads(body.decode("utf-8"))
                            messages_received.append(msg_dict)
                        except Exception:
                            messages_received.append({"raw_body": body.decode("utf-8", errors="ignore")})
                    else:
                        break

                connection.close()
                return messages_received
            except Exception as err:
                logger.warning(f"Falha ao consumir do RabbitMQ real ({err}). Retornando mensagens da Mock Queue.")
                self._is_live_connection = False

        # Consome da fila em memória (Modo Mock)
        count = min(len(self._mock_queue), max_messages)
        for _ in range(count):
            messages_received.append(self._mock_queue.pop(0))

        return messages_received

    def get_queue_status(self) -> Dict[str, Any]:
        """
        Retorna as métricas e estado atual da fila (modo de operação, total de mensagens).

        Retorno:
            Dict[str, Any]: Dicionário com informações sobre host, porta, fila e contagem de mensagens.
        """
        live = self._check_connection()
        message_count = len(self._mock_queue)

        if live:
            try:
                credentials = pika.PlainCredentials(self.user, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    port=self.port,
                    credentials=credentials,
                    socket_timeout=3
                )
                connection = pika.BlockingConnection(parameters)
                channel = connection.channel()
                queue = channel.queue_declare(queue=self.queue_name, durable=True, passive=True)
                message_count = queue.method.message_count
                connection.close()
            except Exception:
                live = False

        return {
            "queue_name": self.queue_name,
            "broker_host": f"{self.host}:{self.port}",
            "is_live_broker": live,
            "mode": "LIVE_AMQP" if live else "MOCK_MEMORY",
            "message_count": message_count
        }
