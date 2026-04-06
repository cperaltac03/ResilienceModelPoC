import json
import os
from typing import Dict, Any

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec
from common.events.schemas import utc_now, new_id
from classifier import FailureClassifier

SERVICE = "failure_classifier"

RESILIENCE_EXCHANGE = "resilience"

IN_ROUTING_KEY = "failure.detected"
IN_QUEUE = "failure_classifier.in"

OUT_ROUTING_KEY = "failure.classified"


def main() -> None:
    settings = Settings()

    log = ElasticLogger(
        service=SERVICE,
        elastic_host=settings.elasticsearch_host,
        index=settings.elastic_index,
    )

    mq = RabbitMQClient(settings)
    mq.connect()

    spec = ConsumeSpec(
        queue=IN_QUEUE,
        exchange=settings.exchange_resilience,
        routing_key=IN_ROUTING_KEY,
        durable=True,
    )
    mq.setup_consumer(spec)

    classifier = FailureClassifier()

    log.log("INFO", "Servicio iniciado")

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        evt = payload
        classification = classifier.classify(evt.get("error"))

        classified = {
            "event_id": new_id(),
            "event_type": "dependency_failure_classified",
            "timestamp": utc_now(),
            "pipeline_id": evt.get("pipeline_id"),
            "run_id": evt.get("run_id"),
            "repo": evt.get("repo"),
            "branch": evt.get("branch"),
            "dependency": evt.get("dependency"),
            "version": evt.get("version"),
            "error": evt.get("error"),
            "category": classification.category,
            "severity": classification.severity,
            "source_event": evt.get("event_id"),
        }

        log.log("INFO", "Fallo clasificado", pipeline_id=classified["pipeline_id"],
                category=classification.category, severity=classification.severity)

        mq.publish_json(
            exchange=settings.exchange_resilience,
            routing_key=OUT_ROUTING_KEY,
            message=classified,
            persistent=True,
        )

    mq.consume(queue=IN_QUEUE, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()

