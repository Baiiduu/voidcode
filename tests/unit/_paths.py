from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"


def with_src_pythonpath(env: dict[str, str] | None = None) -> dict[str, str]:
    merged = dict(os.environ if env is None else env)
    current = merged.get("PYTHONPATH")
    merged["PYTHONPATH"] = f"{SRC_ROOT}{os.pathsep}{current}" if current else str(SRC_ROOT)
    return merged
