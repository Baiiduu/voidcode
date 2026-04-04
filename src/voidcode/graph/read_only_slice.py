"""Deterministic graph runner for one read-only request."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..runtime.events import EventEnvelope
from ..runtime.session import SessionState
from ..tools.contracts import ToolCall, ToolDefinition, ToolResult
from .contracts import GraphRunRequest, GraphRunResult

READ_REQUEST_PATTERN = re.compile(r"^(read|show)\s+(?P<path>.+)$", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class DeterministicReadOnlyPlan:
    tool_call: ToolCall


class DeterministicReadOnlyGraph:
    """A tiny graph that deterministically maps a request onto one read tool."""

    def plan(self, request: GraphRunRequest) -> DeterministicReadOnlyPlan:
        match = READ_REQUEST_PATTERN.match(request.prompt.strip())
        if match is None:
            msg = "unsupported request: use 'read <relative-path>' or 'show <relative-path>'"
            raise ValueError(msg)

        path_text = match.group("path").strip()
        if not path_text:
            raise ValueError("request path must not be empty")

        self._ensure_read_tool_available(request.available_tools)
        return DeterministicReadOnlyPlan(
            tool_call=ToolCall(tool_name="read_file", arguments={"path": path_text})
        )

    def finalize(
        self,
        request: GraphRunRequest,
        tool_result: ToolResult,
        *,
        session: SessionState,
    ) -> GraphRunResult:
        return GraphRunResult(
            session=session,
            events=(
                EventEnvelope(
                    session_id=request.session.session.id,
                    sequence=6,
                    event_type="graph.response_ready",
                    source="graph",
                    payload={"output_preview": tool_result.content or ""},
                ),
            ),
            tool_results=(tool_result,),
            output=tool_result.content,
        )

    def _ensure_read_tool_available(self, tools: tuple[ToolDefinition, ...]) -> None:
        if any(tool.name == "read_file" and tool.read_only for tool in tools):
            return
        raise ValueError("read_file tool is not registered for graph execution")
