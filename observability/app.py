import json
import os
from typing import Dict, Any

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec
from common.events.schemas import utc_now, new_id

SERVICE = "observability"

CICD_EXCHANGE = "cicd"
RESILIENCE_EXCHANGE = "resilience"

IN_ROUTING_KEY = "pipeline.event"
IN_QUEUE = "observability.in"

OUT_ROUTING_KEY = "obs.event"


def normalize_pipeline_event(evt: Dict[str, Any]) -> Dict[str, Any]:
    # Normaliza el evento para el flujo interno
    return {
        "event_id": new_id(),
        "event_type": "observability_event",
        "timestamp": utc_now(),
        "source": "pipeline",
        "pipeline_id": evt.get("pipeline_id"),
        "run_id": evt.get("run_id"),
        "repo": evt.get("repo"),
        "branch": evt.get("branch"),
        "stage": evt.get("stage", "dependencies"),
        "status": evt.get("status"),
        "dependency": evt.get("dependency"),
        "version": evt.get("version"),
        "error": evt.get("error"),
        "raw": evt,
    }


def main() -> None:
    settings = Settings()

    log = ElasticLogger(
        service=SERVICE,
        elastic_host=settings.elasticsearch_host,
        index=settings.elastic_index,
    )

    mq = RabbitMQClient(settings)
    mq.connect()

    # Setup exchanges
    mq.channel.exchange_declare(exchange=settings.exchange_cicd, exchange_type="topic", durable=True)
    mq.channel.exchange_declare(exchange=settings.exchange_resilience, exchange_type="topic", durable=True)

    spec = ConsumeSpec(
        queue=IN_QUEUE,
        exchange=settings.exchange_cicd,
        routing_key=IN_ROUTING_KEY,
        durable=True,
    )
    mq.setup_consumer(spec)

    log.log("INFO", "Servicio iniciado", rabbitmq_host=settings.rabbitmq_host)

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        try:
            incoming = payload  # Already dict from mq.consume
        except Exception:
            incoming = {"raw_body": str(payload)}

        norm = normalize_pipeline_event(incoming)
        log.log("INFO", "Evento de pipeline recibido y normalizado",
                pipeline_id=norm.get("pipeline_id"), run_id=norm.get("run_id"),
                stage=norm.get("stage"), status=norm.get("status"))

        mq.publish_json(
            exchange=settings.exchange_resilience,
            routing_key=OUT_ROUTING_KEY,
            message=norm,
            persistent=True,
        )

    mq.consume(queue=IN_QUEUE, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()