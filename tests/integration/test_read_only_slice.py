"""Integration tests for the deterministic read-only slice."""

from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Protocol, cast


class EventLike(Protocol):
    event_type: str


class SessionLike(Protocol):
    status: str


class RuntimeResponseLike(Protocol):
    events: tuple[EventLike, ...]
    output: str | None
    session: SessionLike


class RuntimeRequestLike(Protocol):
    prompt: str


class RuntimeRequestFactory(Protocol):
    def __call__(self, *, prompt: str) -> RuntimeRequestLike: ...


class RuntimeRunner(Protocol):
    def run(self, request: RuntimeRequestLike) -> RuntimeResponseLike: ...


class RuntimeFactory(Protocol):
    def __call__(self, *, workspace: Path) -> RuntimeRunner: ...


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def _load_runtime_types() -> tuple[RuntimeRequestFactory, RuntimeFactory]:
    contracts_module = importlib.import_module("voidcode.runtime.contracts")
    service_module = importlib.import_module("voidcode.runtime.service")
    runtime_request = cast(RuntimeRequestFactory, contracts_module.RuntimeRequest)
    runtime_class = cast(RuntimeFactory, service_module.VoidCodeRuntime)
    return runtime_request, runtime_class


def test_runtime_executes_read_only_slice_and_emits_events(tmp_path: Path) -> None:
    sample_file = tmp_path / "sample.txt"
    _ = sample_file.write_text("alpha\nbeta\n", encoding="utf-8")
    runtime_request, runtime_class = _load_runtime_types()

    runtime = runtime_class(workspace=tmp_path)
    result = runtime.run(runtime_request(prompt="read sample.txt"))

    assert [event.event_type for event in result.events] == [
        "runtime.request_received",
        "graph.tool_request_created",
        "runtime.tool_lookup_succeeded",
        "runtime.permission_resolved",
        "runtime.tool_completed",
        "graph.response_ready",
    ]
    assert result.session.status == "completed"
    assert result.output == "alpha\nbeta\n"


def test_cli_run_command_prints_events_and_file_contents(tmp_path: Path) -> None:
    sample_file = tmp_path / "sample.txt"
    _ = sample_file.write_text("slice proof\n", encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[2] / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "voidcode",
            "run",
            "read sample.txt",
            "--workspace",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0
    assert "EVENT runtime.request_received" in result.stdout
    assert "EVENT runtime.tool_completed" in result.stdout
    assert "RESULT" in result.stdout
    assert "slice proof" in result.stdout
