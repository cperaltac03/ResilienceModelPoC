from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import requests


@dataclass(frozen=True)
class DecisionContext:
    """
    Contexto mínimo para el motor de decisiones (rule engine).
    Mantenerlo pequeño ayuda a la transparencia y testabilidad.
    """
    category: Optional[str] = None
    severity: Optional[str] = None
    criticality: Optional[str] = None
    branch: Optional[str] = None


class DecisionEngine:
    """
    Motor determinista basado en reglas JSON (Rule Engine Pattern).
    - Evalúa reglas en orden (first-match wins)
    - Match exacto por claves presentes en 'if'
    - Fallback determinista si no hay match
    """

    def __init__(self, rules_service_url: str, timeout_seconds: int = 3):
        self.rules_service_url = rules_service_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def fetch_rules(self) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(f"{self.rules_service_url}/rules", timeout=self.timeout_seconds)
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception:
            # En prototipo, si no hay reglas remotas, se retorna vacío para usar fallback
            return []

    @staticmethod
    def _rule_matches(rule_if: Dict[str, Any], ctx: Dict[str, Any]) -> bool:
        for k, v in (rule_if or {}).items():
            if ctx.get(k) != v:
                return False
        return True

    def decide(self, ctx: DecisionContext, rules: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        ctx_dict = {
            "category": ctx.category,
            "severity": ctx.severity,
            "criticality": ctx.criticality,
            "branch": ctx.branch,
        }

        rules_list = rules if rules is not None else self.fetch_rules()

        for rule in rules_list:
            if self._rule_matches(rule.get("if", {}), ctx_dict):
                then = rule.get("then", {}) or {}
                return then

        # Fallback determinista (coherente con decision_engine/app.py)
        return {"action": "retry", "max_attempts": 2, "backoff_seconds": 2}