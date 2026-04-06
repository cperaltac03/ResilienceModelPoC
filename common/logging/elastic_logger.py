import json
import logging
from typing import Any, Dict, Optional

import requests

from common.events.schemas import utc_now

logging.basicConfig(level=logging.INFO, format="%(message)s")


def log_json(record: Dict[str, Any]) -> None:
    logging.info(json.dumps(record, ensure_ascii=False))


class ElasticLogger:
    """
    Logger simple:
      - siempre imprime JSON a stdout
      - opcionalmente indexa en Elasticsearch (si se configura host)
    """

    def __init__(self, service: str, elastic_host: Optional[str] = None, index: str = "resilience-logs"):
        self.service = service
        self.elastic_host = elastic_host.rstrip("/") if elastic_host else None
        self.index = index

    def log(self, level: str, message: str, **fields: Any) -> None:
        record = {
            "@timestamp": utc_now(),
            "level": level,
            "service": self.service,
            "message": message,
            **fields,
        }
        log_json(record)

        if self.elastic_host:
            try:
                requests.post(f"{self.elastic_host}/{self.index}/_doc", json=record, timeout=2)
            except Exception:
                # No rompemos el flujo del pipeline si ES falla (resiliencia del prototipo)
                pass