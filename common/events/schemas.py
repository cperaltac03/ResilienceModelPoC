import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


def build_envelope(
    *,
    event_type: str,
    payload: Dict[str, Any],
    source: str,
    correlation_id: Optional[str] = None,
    causation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Envelope estándar para eventos:
    - event_id: id del evento actual
    - correlation_id: id compartido por todos los eventos del mismo flujo (p.ej. run_id)
    - causation_id: id del evento que originó este evento (source_event)
    """
    return {
        "event_id": new_id(),
        "event_type": event_type,
        "timestamp": utc_now(),
        "source": source,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "payload": payload,
    }


def flatten_envelope(envelope: Dict[str, Any]) -> Dict[str, Any]:
    """
    Aplana el envelope si quieres compatibilidad con servicios que esperan campos top-level.
    """
    out = dict(envelope)
    payload = out.pop("payload", {}) or {}
    if isinstance(payload, dict):
        out.update(payload)
    return out
