from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DetectionResult:
    is_failure: bool
    reason: str


class DetectionRules:
    """
    Reglas deterministas para detectar fallos relevantes en resolución de dependencias.
    Diseñado para evolucionar sin acoplar el detector a otros servicios.
    """

    def __init__(self, stage_name: str = "dependencies"):
        self.stage_name = stage_name

    def evaluate(self, event: Dict[str, Any]) -> DetectionResult:
        stage = event.get("stage")
        status = event.get("status")
        error = event.get("error")

        if stage != self.stage_name:
            return DetectionResult(False, f"Ignorado: stage != {self.stage_name}")

        if status != "failed":
            return DetectionResult(False, "Ignorado: status != failed")

        if not error:
            return DetectionResult(False, "Ignorado: error vacío")

        return DetectionResult(True, "Fallo de dependencias detectado")

    def extract_dependency_info(self, event: Dict[str, Any]) -> Dict[str, Optional[str]]:
        """
        Extrae campos esperados para el flujo. Esto mantiene el detector robusto ante cambios.
        """
        return {
            "dependency": event.get("dependency"),
            "version": event.get("version"),
            "error": event.get("error"),
        }
