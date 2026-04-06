import json
import os
from typing import Dict, Any

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec
from common.events.schemas import utc_now, new_id
from impact_matrix import ImpactMatrix

SERVICE = "impact_evaluator"

RESILIENCE_EXCHANGE = "resilience"

IN_ROUTING_KEY = "failure.classified"
IN_QUEUE = "impact_evaluator.in"

OUT_ROUTING_KEY = "failure.impact"


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

    impact_matrix = ImpactMatrix()

    log.log("INFO", "Servicio iniciado")

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        evt = payload
        category = evt.get("category")
        severity = evt.get("severity")
        branch = evt.get("branch")

        # Evaluar impacto usando la matriz
        impact = impact_matrix.evaluate(category, severity, branch)

        impact_event = {
            "event_id": new_id(),
            "event_type": "dependency_failure_impact",
            "timestamp": utc_now(),
            "pipeline_id": evt.get("pipeline_id"),
            "run_id": evt.get("run_id"),
            "repo": evt.get("repo"),
            "branch": branch,
            "dependency": evt.get("dependency"),
            "version": evt.get("version"),
            "error": evt.get("error"),
            "category": category,
            "severity": severity,
            "impact_score": impact.impact_score,
            "criticality": impact.criticality,
            "source_event": evt.get("event_id"),
        }

        log.log("INFO", "Impacto evaluado", 
                pipeline_id=impact_event["pipeline_id"],
                category=category, 
                severity=severity,
                impact_score=impact.impact_score,
                criticality=impact.criticality)

        mq.publish_json(
            exchange=settings.exchange_resilience,
            routing_key=OUT_ROUTING_KEY,
            message=impact_event,
            persistent=True,
        )

    mq.consume(queue=IN_QUEUE, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()