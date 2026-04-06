import os
from typing import Dict, Any

from common.config import Settings
from common.events.event_types import RoutingKeys
from common.events.schemas import utc_now, new_id
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec

import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rules.detection_rules import DetectionRules

SERVICE = "failure_detector"


def main() -> None:
    settings = Settings()

    log = ElasticLogger(
        service=SERVICE,
        elastic_host=settings.elasticsearch_host,
        index=settings.elastic_index,
    )

    mq = RabbitMQClient(settings)
    mq.connect()

    # Setup idempotente (exchange/queue/bind)
    in_queue = os.getenv("DETECTOR_QUEUE", "detector.in")
    in_routing_key = os.getenv("DETECTOR_IN_ROUTING_KEY", RoutingKeys.OBS_EVENT)
    out_routing_key = os.getenv("DETECTOR_OUT_ROUTING_KEY", RoutingKeys.FAILURE_DETECTED)

    spec = ConsumeSpec(
        queue=in_queue,
        exchange=settings.exchange_resilience,  # "resilience"
        routing_key=in_routing_key,             # "obs.event"
        durable=True,
    )
    mq.setup_consumer(spec)

    detection_rules = DetectionRules()

    log.log("INFO", "Servicio iniciado",
            rabbitmq_host=settings.rabbitmq_host,
            exchange=settings.exchange_resilience,
            in_queue=in_queue,
            in_routing_key=in_routing_key,
            out_routing_key=out_routing_key)

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        # payload viene del flujo interno (observabilidad)
        pipeline_id = payload.get("pipeline_id")
        run_id = payload.get("run_id")

        result = detection_rules.evaluate(payload)

        if result.is_failure:
            dep_info = detection_rules.extract_dependency_info(payload)
            detected = {
                "event_id": new_id(),
                "event_type": "dependency_failure_detected",
                "timestamp": utc_now(),
                "pipeline_id": pipeline_id,
                "run_id": run_id,
                "repo": payload.get("repo"),
                "branch": payload.get("branch"),
                "dependency": dep_info.get("dependency"),
                "version": dep_info.get("version"),
                "error": dep_info.get("error"),
                # Trazabilidad (ciclo de feedback / auditoría)
                "source_event": payload.get("event_id"),
            }

            log.log(
                "INFO",
                "Fallo de dependencias detectado",
                pipeline_id=pipeline_id,
                run_id=run_id,
                error=detected.get("error"),
                dependency=detected.get("dependency"),
                version=detected.get("version"),
            )

            mq.publish_json(
                exchange=settings.exchange_resilience,
                routing_key=out_routing_key,
                message=detected,
                persistent=True,
            )
        else:
            log.log(
                "INFO",
                "Evento ignorado",
                pipeline_id=pipeline_id,
                run_id=run_id,
                reason=result.reason,
            )

    # Consumir con QoS / ack manual (RabbitMQClient hace ack si auto_ack=False)
    mq.consume(queue=in_queue, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()