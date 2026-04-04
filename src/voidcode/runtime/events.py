from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

type EventSource = Literal["runtime", "graph", "tool"]


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    session_id: str
    sequence: int
    event_type: str
    source: EventSource
    payload: dict[str, object] = field(default_factory=dict)
