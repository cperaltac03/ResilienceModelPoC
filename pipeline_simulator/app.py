import json
import os
import time
import random
from typing import Dict, Any

from common.config import Settings
from common.logging import ElasticLogger
from common.messaging import RabbitMQClient
from common.events.schemas import utc_now, new_id

SERVICE = "pipeline_simulator"

CICD_EXCHANGE = "cicd"
OUT_ROUTING_KEY = "pipeline.event"

INTERVAL = int(os.getenv("SIMULATOR_INTERVAL", "15"))
REPO = os.getenv("SIM_REPO", "org/demo-repo")
BRANCH = os.getenv("SIM_BRANCH", "main")


def generate_event() -> Dict[str, Any]:
    pipeline_id = f"build-{random.randint(1000, 9999)}"
    run_id = new_id()
    stage = "dependencies"

    # 70% falla, 30% éxito (para mostrar ambos casos)
    failed = random.random() < 0.7

    dependency = random.choice(["requests", "numpy", "pandas", "fastapi", "pika"])
    version = random.choice(["1.0.0", "2.31.0", "0.110.0", "3.12.1", "2.0.7"])

    if failed:
        error = random.choice([
            "ReadTimeoutError: HTTPSConnectionPool(host='pypi.org', port=443): Read timed out.",
            "Failed to transfer file: Connect timed out",
            "Could not GET 'https://repo.maven.apache.org/...'. Read timed out",
            "npm ERR! network timeout at: https://registry.npmjs.org/lodash",
            "ConnectionError: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))",
            "Connection reset -> [Help 1]",
            "Connection reset by peer",
            "npm ERR! network request to https://registry.npmjs.org/react failed, reason: socket hang up",
            "ERROR: Could not find a version that satisfies the requirement package-name (from versions: none)",
            "Could not find artifact org.example:lib:jar:1.0 in central",
            "Could not find org.example:lib:1.0.",
            "npm ERR! 404 Not Found - GET https://registry.npmjs.org/package-name - Not found",
            "ERROR: Cannot install packageA and packageB because these package versions have conflicting dependencies.",
            "Dependency convergence error for org.example:lib",
            "Conflict found for module 'org.example:lib'. Versions 1.0 and 2.0",
            "npm ERR! ERESOLVE unable to resolve dependency tree",
            "ERROR: THESE PACKAGES DO NOT MATCH THE HASHES FROM THE REQUIREMENTS FILE.",
            "Checksum validation failed, expected <hash> but is <hash>",
            "Checksum failed for file 'lib-1.0.jar'",
            "npm ERR! Integrity checksum failed when using sha512",
        ])
        status = "failed"
    else:
        error = None
        status = "success"

    return {
        "event_type": "pipeline_run",
        "timestamp": utc_now(),
        "pipeline_id": pipeline_id,
        "run_id": run_id,
        "repo": REPO,
        "branch": BRANCH,
        "stage": stage,
        "status": status,
        "dependency": dependency,
        "version": version,
        "error": error,
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

    # Setup exchange
    mq.channel.exchange_declare(exchange=settings.exchange_cicd, exchange_type="topic", durable=True)

    log.log("INFO", "Simulador iniciado", interval=INTERVAL)

    while True:
        evt = generate_event()
        mq.publish_json(
            exchange=settings.exchange_cicd,
            routing_key=OUT_ROUTING_KEY,
            message=evt,
            persistent=True,
        )
        log.log("INFO", "Evento publicado", routing_key=OUT_ROUTING_KEY, pipeline_id=evt["pipeline_id"], status=evt["status"])
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()