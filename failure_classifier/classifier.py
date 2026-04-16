from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Classification:
    category: str
    severity: str


class FailureClassifier:
    """
    Clasificador determinista por reglas simples (sin IA).
    Basado en patrones en el mensaje de error.
    """

    def classify(self, error: Optional[str]) -> Classification:
        e = (error or "").lower()

        if "timeout" in e or "timed out" in e or "connect timed out" in e or "network timeout" in e:
            category = "Timeout"
        elif "connection aborted" in e or "connection reset" in e or "reset by peer" in e or "socket hang up" in e:
            category = "Connection lost"
        elif "404" in e or "not found" in e or "could not find" in e:
            category = "404"
        elif "version conflict" in e or "conflicting dependencies" in e or "dependency convergence" in e or "conflict found" in e or "unable to resolve dependency tree" in e or "eresolve" in e:
            category = "Version conflict"
        elif "checksum" in e or "integrity checksum failed" in e or "hash mismatch" in e or "do not match the hashes" in e:
            category = "Checksum mismatch"
        else:
            category = "UNKNOWN"

        severity = self.base_severity(category)
        return Classification(category=category, severity=severity)

    @staticmethod
    def base_severity(category: str) -> str:
        return {
            "Timeout": "MEDIUM",
            "Connection lost": "MEDIUM",
            "404": "HIGH",
            "Version conflict": "HIGH",
            "Checksum mismatch": "HIGH",
            "UNKNOWN": "LOW",
        }.get(category, "LOW")