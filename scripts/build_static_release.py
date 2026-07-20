#!/usr/bin/env python3
"""Build a production static release with its safe runtime configuration first."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    npm = shutil.which("npm")
    if not npm:
        print("npm was not found on PATH.", file=sys.stderr)
        return 1

    runtime_config = REPO_ROOT / "scripts" / "write_runtime_config.py"
    validate = REPO_ROOT / "scripts" / "validate_static_release.py"
    edge_preflight = REPO_ROOT / "scripts" / "preflight_public_edge.py"
    environment = os.environ.copy()
    environment["APP_ENV"] = "production"

    steps = [
        [sys.executable, str(runtime_config), "--environment", "production"],
        [npm, "run", "build"],
        [sys.executable, str(validate), "--out-dir", str(REPO_ROOT / "frontend" / "out")],
        [sys.executable, str(edge_preflight), "--api-only"],
    ]
    for index, command in enumerate(steps):
        cwd = REPO_ROOT / "frontend" if index == 1 else REPO_ROOT
        print("+ " + " ".join(command))
        completed = subprocess.run(command, cwd=cwd, env=environment)
        if completed.returncode:
            return completed.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
