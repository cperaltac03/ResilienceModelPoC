import json
import os
import time
from typing import Dict, Any

import pika
import psycopg2

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient, ConsumeSpec

SERVICE = "event_registry"

RESILIENCE_EXCHANGE = "resilience"
IN_ROUTING_KEY = "resilience.#"
IN_QUEUE = "event_registry.in"


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
        CREATE TABLE IF NOT EXISTS events_audit (
            id SERIAL PRIMARY KEY,
            received_at TIMESTAMPTZ DEFAULT NOW(),
            routing_key TEXT,
            event_type TEXT,
            pipeline_id TEXT,
            run_id TEXT,
            payload JSONB
        );
        """)
    conn.commit()


def save_event(conn, routing_key: str, evt: Dict[str, Any]) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO events_audit (routing_key, event_type, pipeline_id, run_id, payload) VALUES (%s,%s,%s,%s,%s)",
            (routing_key, evt.get("event_type"), evt.get("pipeline_id"), evt.get("run_id"), json.dumps(evt)),
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
        routing_key="#",
        durable=True,
    )
    mq.setup_consumer(spec)

    log.log("INFO", "Servicio iniciado", rabbitmq_host=settings.rabbitmq_host, postgres_host=settings.postgres_host)

    def on_message(payload: Dict[str, Any], routing_key: str) -> None:
        try:
            evt = payload
        except Exception:
            evt = {"raw_body": str(payload)}

        try:
            save_event(db, routing_key, evt)
            log.log("INFO", "Evento auditado", routing_key=routing_key, event_type=evt.get("event_type"), pipeline_id=evt.get("pipeline_id"))
        except Exception as e:
            log.log("ERROR", "Error guardando auditoría", error=str(e), routing_key=routing_key)

    mq.consume(queue=IN_QUEUE, on_message=on_message, prefetch=settings.prefetch_count, auto_ack=False)


if __name__ == "__main__":
    main()
    main()