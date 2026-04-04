from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from ..runtime.events import EventEnvelope
from ..runtime.session import SessionState
from ..tools.contracts import ToolDefinition, ToolResult


@dataclass(frozen=True, slots=True)
class GraphRunRequest:
    session: SessionState
    prompt: str
    available_tools: tuple[ToolDefinition, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class GraphRunResult:
    session: SessionState
    events: tuple[EventEnvelope, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()
    output: str | None = None


@runtime_checkable
class GraphRunner(Protocol):
    def run(self, request: GraphRunRequest) -> GraphRunResult: ...
