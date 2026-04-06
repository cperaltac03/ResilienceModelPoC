import os
from typing import Dict, Any

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec
from common.events.schemas import utc_now, new_id

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from decision_engine import DecisionEngine, DecisionContext

SERVICE = "decision_engine"

RESILIENCE_EXCHANGE = "resilience"

IN_ROUTING_KEY = "failure.classified"
IN_QUEUE = "decision_engine.in"

OUT_ROUTING_KEY = "remediation.command"


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

    engine = DecisionEngine(settings.rules_service_url)

    log.log("INFO", "Servicio iniciado")

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        evt = payload
        category = evt.get("category")
        severity = evt.get("severity")
        branch = evt.get("branch")

        # Crear contexto para el motor de decisiones
        ctx = DecisionContext(
            category=category,
            severity=severity,
            branch=branch,
        )

        # Decidir acción de remediación
        decision = engine.decide(ctx)

        command = {
            "event_id": new_id(),
            "event_type": "remediation_command",
            "timestamp": utc_now(),
            "pipeline_id": evt.get("pipeline_id"),
            "run_id": evt.get("run_id"),
            "repo": evt.get("repo"),
            "branch": evt.get("branch"),
            "dependency": evt.get("dependency"),
            "version": evt.get("version"),
            "failure": {
                "category": category,
                "severity": severity,
            },
            "decision": decision,
            "source_event": evt.get("event_id"),
        }

        log.log("INFO", "Decisión tomada", pipeline_id=command["pipeline_id"], action=decision.get("action"), category=category, severity=severity)

        mq.publish_json(
            exchange=settings.exchange_resilience,
            routing_key=OUT_ROUTING_KEY,
            message=command,
            persistent=True,
        )

    mq.consume(queue=IN_QUEUE, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()