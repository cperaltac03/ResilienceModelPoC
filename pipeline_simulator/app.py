import os
import random
import threading
import time
from typing import Dict, Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import uvicorn

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
SIMULATOR_HTTP_PORT = int(os.getenv("SIMULATOR_HTTP_PORT", "8001"))
SIMULATOR_DISABLE_LOOP = os.getenv("SIMULATOR_DISABLE_LOOP", "false").lower() in ("1", "true", "yes")

app = FastAPI(title="Pipeline Simulator", version="1.0.0")
settings = Settings()


class SimulationRequest(BaseModel):
    repo: str | None = Field(None, description="Repository full name")
    branch: str | None = Field(None, description="Branch name")
    status: str | None = Field(None, description="Pipeline status: success or failed")
    dependency: str | None = Field(None, description="Dependency name")
    version: str | None = Field(None, description="Dependency version")
    stage: str | None = Field(None, description="Pipeline stage")
    pipeline_id: str | None = Field(None, description="Pipeline identifier")
    run_id: str | None = Field(None, description="Run identifier")


class SimulationResponse(BaseModel):
    ok: bool
    event: Dict[str, Any]



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


def build_event(overrides: Dict[str, Any] | None = None) -> Dict[str, Any]:
    event = generate_event()
    for key, value in (overrides or {}).items():
        if value is not None:
            event[key] = value
    return event


def publish_event(event: Dict[str, Any]) -> None:
    mq = RabbitMQClient(settings)
    mq.connect()
    mq.channel.exchange_declare(exchange=settings.exchange_cicd, exchange_type="topic", durable=True)
    mq.publish_json(
        exchange=settings.exchange_cicd,
        routing_key=OUT_ROUTING_KEY,
        message=event,
        persistent=True,
    )
    mq.close()


def start_periodic_emitter() -> None:
    log = ElasticLogger(
        service=SERVICE,
        elastic_host=settings.elasticsearch_host,
        index=settings.elastic_index,
    )

    mq = RabbitMQClient(settings)
    mq.connect()
    mq.channel.exchange_declare(exchange=settings.exchange_cicd, exchange_type="topic", durable=True)

    log.log("INFO", "Simulador periódico iniciado", interval=INTERVAL)

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


@app.on_event("startup")
def startup_event() -> None:
    if SIMULATOR_DISABLE_LOOP:
        return

    thread = threading.Thread(target=start_periodic_emitter, daemon=True)
    thread.start()


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "service": SERVICE, "http_port": SIMULATOR_HTTP_PORT}


@app.post("/simulate", response_model=SimulationResponse)
def simulate(payload: SimulationRequest) -> Dict[str, Any]:
    if payload.status not in (None, "success", "failed"):
        raise HTTPException(status_code=400, detail="status must be 'success' or 'failed'")

    event = build_event(payload.dict(exclude_none=True))
    publish_event(event)
    return {"ok": True, "event": event}


def main() -> None:
    uvicorn.run(app, host="0.0.0.0", port=SIMULATOR_HTTP_PORT)


if __name__ == "__main__":
    main()