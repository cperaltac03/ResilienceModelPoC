import json
import os
import time
from typing import Dict, Any

import psycopg2

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec
from common.events.schemas import utc_now, new_id
from failure_solver.actions import clean_cache_action, dependency_substitution_action, retry_action

SERVICE = "failure_solver"

RESILIENCE_EXCHANGE = "resilience"

IN_ROUTING_KEY = "remediation.command"
IN_QUEUE = "failure_solver.in"

OUT_ROUTING_KEY = "remediation.result"


def db_connect(settings: Settings):
    for attempt in range(1, settings.connect_retries + 1):
        try:
            return psycopg2.connect(
                host=settings.postgres_host,
                dbname=settings.postgres_db,
                user=settings.postgres_user,
                password=settings.postgres_password,
            )
        except Exception as e:
            print(f"Postgres no disponible, reintentando... attempt={attempt}, error={e}")
            time.sleep(settings.connect_retry_delay_seconds)
    raise RuntimeError("No se pudo conectar a Postgres")


def ensure_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS remediation_actions (
            id SERIAL PRIMARY KEY,
            event_id TEXT,
            pipeline_id TEXT,
            run_id TEXT,
            action TEXT,
            status TEXT,
            details JSONB,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """)
    conn.commit()


def execute_action(decision: Dict[str, Any], pipeline_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    action = (decision or {}).get("action", "retry")
    if action == "retry":
        return retry_action(decision)

    if action == "increase_timeout_and_retry":
        return retry_action(decision, timeout_increased=True)

    if action == "change_mirror_and_retry":
        return retry_action(decision, mirror_changed=True)

    if action == "validate_dependency_and_fallback":
        time.sleep(1)
        fallback = dependency_substitution_action({"action": "dependency_substitution"}, pipeline_context)
        return {
            "action": action,
            "validated": True,
            "fallback_used": True,
            "fallback": fallback,
            "result": "success",
        }

    if action == "finalize_pipeline":
        time.sleep(1)
        return {
            "action": action,
            "pipeline_finalized": True,
            "pipeline_id": (pipeline_context or {}).get("pipeline_id"),
            "run_id": (pipeline_context or {}).get("run_id"),
            "result": "failed",
        }

    if action == "clean_cache_and_retry":
        return clean_cache_action(decision)

    if action == "cache_clean":
        return clean_cache_action(decision)

    if action == "dependency_substitution":
        return dependency_substitution_action(decision, pipeline_context)

    return {"action": action, "result": "no_op"}


def save_action(conn, evt_id: str, pipeline_id: str, run_id: str, action: str, status: str, details: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO remediation_actions (event_id, pipeline_id, run_id, action, status, details) VALUES (%s,%s,%s,%s,%s,%s)",
            (evt_id, pipeline_id, run_id, action, status, json.dumps(details)),
        )
    conn.commit()


def main() -> None:
    settings = Settings()

    log = ElasticLogger(
        service=SERVICE,
        elastic_host=settings.elasticsearch_host,
        index=settings.elastic_index,
    )

    db = db_connect(settings)
    ensure_tables(db)

    mq = RabbitMQClient(settings)
    mq.connect()

    spec = ConsumeSpec(
        queue=IN_QUEUE,
        exchange=settings.exchange_resilience,
        routing_key=IN_ROUTING_KEY,
        durable=True,
    )
    mq.setup_consumer(spec)

    log.log("INFO", "Servicio iniciado", postgres_host=settings.postgres_host)

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        evt = payload
        decision = evt.get("decision", {})
        outcome = execute_action(decision, evt)

        result_status = outcome.get("result", "unknown")
        action_name = outcome.get("action", "unknown")

        result = {
            "event_id": new_id(),
            "event_type": "remediation_result",
            "timestamp": utc_now(),
            "pipeline_id": evt.get("pipeline_id"),
            "run_id": evt.get("run_id"),
            "repo": evt.get("repo"),
            "branch": evt.get("branch"),
            "dependency": evt.get("dependency"),
            "version": evt.get("version"),
            "decision": decision,
            "outcome": outcome,
            "status": result_status,
            "source_event": evt.get("event_id"),
        }

        log.log("INFO", "Remediación ejecutada", pipeline_id=result["pipeline_id"], action=action_name, status=result_status)

        try:
            save_action(db, result["event_id"], result["pipeline_id"], result["run_id"], action_name, result_status, result)
        except Exception as e:
            log.log("ERROR", "Error guardando en Postgres", error=str(e))

        mq.publish_json(
            exchange=settings.exchange_resilience,
            routing_key=OUT_ROUTING_KEY,
            message=result,
            persistent=True,
        )

    mq.consume(queue=IN_QUEUE, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()