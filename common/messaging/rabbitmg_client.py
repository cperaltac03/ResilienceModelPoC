import json
import time
from dataclasses import dataclass
from typing import Callable, Optional

import pika

from common.config.settings import Settings


@dataclass
class ConsumeSpec:
    queue: str
    exchange: str
    routing_key: str
    durable: bool = True


class RabbitMQClient:
    """
    Wrapper minimalista de pika.BlockingConnection.
    Recomendado para prototipos: simple, robusto, idempotente.
    """

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings()
        self._connection: Optional[pika.BlockingConnection] = None
        self._channel: Optional[pika.adapters.blocking_connection.BlockingChannel] = None

    @property
    def channel(self):
        if not self._channel:
            raise RuntimeError("RabbitMQ channel no inicializado. Llama connect() primero.")
        return self._channel

    def connect(self) -> None:
        creds = pika.PlainCredentials(self.settings.rabbitmq_user, self.settings.rabbitmq_password)
        params = pika.ConnectionParameters(
            host=self.settings.rabbitmq_host,
            port=self.settings.rabbitmq_port,
            credentials=creds,
            heartbeat=self.settings.rabbitmq_heartbeat,
        )

        for attempt in range(1, self.settings.connect_retries + 1):
            try:
                self._connection = pika.BlockingConnection(params)
                self._channel = self._connection.channel()
                return
            except Exception as e:
                print(json.dumps({
                    "@timestamp": time.time(),
                    "level": "WARN",
                    "service": "common.rabbitmq",
                    "message": "RabbitMQ no disponible, reintentando...",
                    "attempt": attempt,
                    "error": str(e),
                }))
                time.sleep(self.settings.connect_retry_delay_seconds)

        raise RuntimeError("No se pudo conectar a RabbitMQ tras múltiples reintentos.")

    def close(self) -> None:
        try:
            if self._channel and self._channel.is_open:
                self._channel.close()
        except Exception:
            pass
        try:
            if self._connection and self._connection.is_open:
                self._connection.close()
        except Exception:
            pass

    # ---------- Declaración idempotente ----------

    def declare_topic_exchange(self, name: str, durable: bool = True) -> None:
        self.channel.exchange_declare(exchange=name, exchange_type="topic", durable=durable)

    def declare_queue(self, name: str, durable: bool = True) -> None:
        self.channel.queue_declare(queue=name, durable=durable)

    def bind_queue(self, queue: str, exchange: str, routing_key: str) -> None:
        self.channel.queue_bind(queue=queue, exchange=exchange, routing_key=routing_key)

    def setup_consumer(self, spec: ConsumeSpec) -> None:
        self.declare_topic_exchange(spec.exchange, durable=spec.durable)
        self.declare_queue(spec.queue, durable=spec.durable)
        self.bind_queue(spec.queue, spec.exchange, spec.routing_key)

    # ---------- Publicación / Consumo ----------

    def publish_json(self, exchange: str, routing_key: str, message: dict, persistent: bool = True) -> None:
        body = json.dumps(message, ensure_ascii=False).encode("utf-8")
        props = pika.BasicProperties(
            content_type="application/json",
            delivery_mode=2 if persistent else 1,
        )
        self.channel.basic_publish(exchange=exchange, routing_key=routing_key, body=body, properties=props)

    def consume(
        self,
        queue: str,
        on_message: Callable[[dict, str], None],
        prefetch: Optional[int] = None,
        auto_ack: bool = False,
    ) -> None:
        """
        on_message(payload_dict, routing_key)
        """
        self.channel.basic_qos(prefetch_count=prefetch or self.settings.prefetch_count)

        def _callback(ch, method, properties, body: bytes):
            routing_key = method.routing_key
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {"raw_body": body.decode("utf-8", errors="ignore")}

            on_message(payload, routing_key)

            if not auto_ack:
                ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=queue, on_message_callback=_callback, auto_ack=auto_ack)
        self.channel.start_consuming()