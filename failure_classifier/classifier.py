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

        if "timeout" in e or "connection" in e or "reset" in e:
            category = "NETWORK"
        elif "404" in e or "not found" in e:
            category = "MISSING_ARTIFACT"
        elif "version conflict" in e or "conflict" in e:
            category = "VERSION_CONFLICT"
        elif "checksum" in e or "hash mismatch" in e:
            category = "INTEGRITY"
        else:
            category = "UNKNOWN"

        severity = self.base_severity(category)
        return Classification(category=category, severity=severity)

    @staticmethod
    def base_severity(category: str) -> str:
        return {
            "NETWORK": "MEDIUM",
            "MISSING_ARTIFACT": "HIGH",
            "VERSION_CONFLICT": "HIGH",
            "INTEGRITY": "HIGH",
            "UNKNOWN": "LOW",
        }.get(category, "LOW")