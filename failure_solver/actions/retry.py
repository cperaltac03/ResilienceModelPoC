from __future__ import annotations

import time
from typing import Any, Dict


def retry_action(decision: Dict[str, Any], *, timeout_increased: bool = False, mirror_changed: bool = False) -> Dict[str, Any]:
    attempts = int((decision or {}).get("max_attempts", 2))
    backoff = int((decision or {}).get("backoff_seconds", 2))

    for _ in range(max(1, attempts)):
        time.sleep(min(3, backoff))

    outcome: Dict[str, Any] = {
        "action": (decision or {}).get("action", "retry"),
        "attempts": attempts,
        "backoff_seconds": backoff,
        "result": "success",
    }

    if timeout_increased:
        outcome["timeout_increased"] = True

    if mirror_changed:
        outcome["mirror_changed"] = True

    return outcome
