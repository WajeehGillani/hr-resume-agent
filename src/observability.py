# src/observability.py
from __future__ import annotations
import json, time, uuid
from pathlib import Path
from typing import Any, Dict

ARTIFACTS = Path(__file__).resolve().parents[1] / "artifacts"
ARTIFACTS.mkdir(parents=True, exist_ok=True)

class LocalTracer:
    def __init__(self):
        self.path = ARTIFACTS / f"run_{int(time.time())}_{uuid.uuid4().hex[:6]}.jsonl"

    def log(self, kind: str, payload: Dict[str, Any]):
        rec = {"ts": time.time(), "kind": kind, **payload}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

    def log_node(self, name: str, event: str, **kwargs):
        self.log("node", {"name": name, "event": event, **kwargs})

    def log_tool(self, name: str, **kwargs):
        self.log("tool", {"name": name, **kwargs})

_tracer = LocalTracer()

def get_tracer() -> LocalTracer:
    return _tracer
