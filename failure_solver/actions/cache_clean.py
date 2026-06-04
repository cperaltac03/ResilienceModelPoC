from __future__ import annotations

import time
from typing import Any, Dict


def clean_cache_action(decision: Dict[str, Any]) -> Dict[str, Any]:
    attempts = int((decision or {}).get("max_attempts", 1))
    backoff = int((decision or {}).get("backoff_seconds", 2))

    time.sleep(min(3, backoff))

    return {
        "action": (decision or {}).get("action", "clean_cache"),
        "attempts": attempts,
        "backoff_seconds": backoff,
        "cache_cleaned": True,
        "result": "success",
    }
