from __future__ import annotations

import argparse
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import cast

from . import __version__
from .runtime.contracts import RuntimeRequest
from .runtime.service import VoidCodeRuntime

Handler = Callable[[argparse.Namespace], int]


def _format_event(event_type: str, source: str, data: dict[str, object]) -> str:
    suffix = " ".join(f"{key}={value}" for key, value in sorted(data.items()))
    if suffix:
        return f"EVENT {event_type} source={source} {suffix}"
    return f"EVENT {event_type} source={source}"


def _handle_run_command(args: argparse.Namespace) -> int:
    workspace = cast(Path, args.workspace)
    request_text = cast(str, args.request)
    runtime = VoidCodeRuntime(workspace=workspace)
    result = runtime.run(RuntimeRequest(prompt=request_text))

    for event in result.events:
        print(_format_event(event.event_type, event.source, event.payload))

    print("RESULT")
    print(result.output or "", end="")
    if result.output and not result.output.endswith("\n"):
        print()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="voidcode",
        description="Voidcode command-line interface.",
    )
    _ = parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser(
        "run",
        help="Run the deterministic local read-only slice.",
    )
    _ = run_parser.add_argument(
        "request",
        help="Simple deterministic request such as 'read README.md'.",
    )
    _ = run_parser.add_argument(
        "--workspace",
        type=Path,
        default=Path.cwd(),
        help="Workspace root used to resolve relative read paths.",
    )
    run_parser.set_defaults(handler=_handle_run_command)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = cast(Handler | None, getattr(args, "handler", None))
    if handler is None:
        parser.print_help()
        return 0
    return handler(args)
