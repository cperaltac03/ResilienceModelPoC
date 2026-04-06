import json
import os
from typing import Any, List, Dict

from fastapi import FastAPI, HTTPException

RULES_FILE = os.getenv("RULES_FILE", "/app/rules.json")

app = FastAPI(title="Modulo de Reglas", version="1.0.0")


def read_rules() -> List[Dict[str, Any]]:
    if not os.path.exists(RULES_FILE):
        return []
    with open(RULES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def write_rules(rules: List[Dict[str, Any]]) -> None:
    with open(RULES_FILE, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "rules_file": RULES_FILE,
        "rules_count": len(read_rules()),
    }


@app.get("/rules")
def get_rules():
    return read_rules()


@app.put("/rules")
def replace_rules(rules: List[Dict[str, Any]]):
    try:
        write_rules(rules)
        return {"ok": True, "count": len(rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/rules")
def append_rule(rule: Dict[str, Any]):
    try:
        rules = read_rules()
        rules.append(rule)
        write_rules(rules)
        return {"ok": True, "count": len(rules)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))