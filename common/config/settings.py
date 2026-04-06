import os
from dataclasses import dataclass


def _env(key: str, default: str | None = None) -> str | None:
    v = os.getenv(key)
    return v if v is not None and v != "" else default


def _env_int(key: str, default: int) -> int:
    v = _env(key)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    """
    Configuración centralizada del prototipo.
    Se alimenta de variables de entorno (Docker Compose).
    """

    # RabbitMQ
    rabbitmq_host: str = _env("RABBITMQ_HOST", "localhost") or "localhost"
    rabbitmq_port: int = _env_int("RABBITMQ_PORT", 5672)
    rabbitmq_user: str = _env("RABBITMQ_USER", "guest") or "guest"
    rabbitmq_password: str = _env("RABBITMQ_PASSWORD", "guest") or "guest"
    rabbitmq_heartbeat: int = _env_int("RABBITMQ_HEARTBEAT", 60)

    # Exchanges
    exchange_cicd: str = _env("CICD_EXCHANGE", "cicd") or "cicd"
    exchange_resilience: str = _env("RESILIENCE_EXCHANGE", "resilience") or "resilience"

    # Observabilidad
    elasticsearch_host: str | None = _env("ELASTICSEARCH_HOST", None)
    elastic_index: str = _env("ELASTIC_INDEX", "resilience-logs") or "resilience-logs"

    # Rules module (API)
    rules_service_url: str = _env("RULES_SERVICE_URL", "http://rules_manager:8000") or "http://rules_manager:8000"

    # Postgres (when applicable)
    postgres_host: str = _env("POSTGRES_HOST", "localhost") or "localhost"
    postgres_db: str = _env("POSTGRES_DB", "resilience") or "resilience"
    postgres_user: str = _env("POSTGRES_USER", "resilience_user") or "resilience_user"
    postgres_password: str = _env("POSTGRES_PASSWORD", "resilience_pass") or "resilience_pass"

    # Consumo
    prefetch_count: int = _env_int("PREFETCH_COUNT", 10)

    # Reintentos (120 intentos * 1 segundo = 2 minutos)
    connect_retries: int = _env_int("CONNECT_RETRIES", 120)
    connect_retry_delay_seconds: int = _env_int("CONNECT_RETRY_DELAY_SECONDS", 1)