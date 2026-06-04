from __future__ import annotations

import time
from typing import Any, Dict


SUBSTITUTION_MAP = {
    "requests": "requests-mirror",
    "numpy": "numpy-stable",
    "pandas": "pandas-stable",
    "fastapi": "fastapi-lts",
    "pika": "pika-reliable",
}


def dependency_substitution_action(decision: Dict[str, Any], pipeline_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    context = pipeline_context or {}
    dependency = context.get("dependency") or (decision or {}).get("dependency") or "unknown"
    substitute = SUBSTITUTION_MAP.get(dependency, f"{dependency}-alt")

    time.sleep(1)

    return {
        "action": (decision or {}).get("action", "dependency_substitution"),
        "dependency": dependency,
        "substitute_dependency": substitute,
        "substituted": True,
        "result": "success",
    }
