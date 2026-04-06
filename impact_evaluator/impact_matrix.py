from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Impact:
    impact_score: int
    criticality: str


class ImpactMatrix:
    """
    Evaluador determinista de impacto (sin IA).
    Combina severidad, categoría y criticidad por rama.
    """

    def evaluate(self, category: Optional[str], severity: Optional[str], branch: Optional[str]) -> Impact:
        base = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}.get((severity or "").upper(), 1)

        cat_weight = {
            "NETWORK": 1,
            "MISSING_ARTIFACT": 2,
            "VERSION_CONFLICT": 2,
            "INTEGRITY": 3,
            "UNKNOWN": 1,
        }.get((category or "UNKNOWN").upper(), 1)

        critical_branch_bonus = 1 if (branch or "").lower() in ("main", "master", "release") else 0

        score = min(5, base + cat_weight + critical_branch_bonus)

        if score >= 5:
            crit = "CRITICAL"
        elif score >= 4:
            crit = "HIGH"
        elif score >= 3:
            crit = "MEDIUM"
        else:
            crit = "LOW"

        return Impact(impact_score=score, criticality=crit)
