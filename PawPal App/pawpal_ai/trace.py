from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class TraceEntry:
    ts: float
    component: str
    message: str
    detail: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


class TraceLog:
    """Append-only trace for Explainability tab."""

    def __init__(self, request_id: Optional[str] = None):
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.entries: List[TraceEntry] = []

    def add(self, component: str, message: str, **detail: Any) -> None:
        self.entries.append(
            TraceEntry(ts=time.time(), component=component, message=message, detail=detail or {})
        )

    def last_json(self) -> str:
        return json.dumps([asdict(e) for e in self.entries], indent=2)
