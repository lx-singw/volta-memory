#!/usr/bin/env python3
"""Bundle the static Volta UI into Function Compute for a zero-domain demo.

The browser, API, and session cookie share the Function Compute ``fcapp.run``
origin.  This is intentionally separate from the OSS/CDN release workflow:
it is a functional, Alibaba-hosted hackathon deployment when a custom domain
is unavailable, not a claim that CDN/API Gateway are configured.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
FRONTEND_OUT = FRONTEND_DIR / "out"
STATIC_TARGET = REPO_ROOT / "backend" / "app" / "static"
REQUIRED_FILES = (
    "index.html",
    "memory/index.html",
    "showcase/index.html",
    "try/index.html",
    "auth/verify/index.html",
    "runtime-config.js",
)


def _assert_safe_target(target: Path) -> None:
    root = REPO_ROOT.resolve()
    resolved = target.resolve()
    if root not in resolved.parents or resolved == root:
        raise RuntimeError(f"Refusing to replace a path outside the repository: {resolved}")


def main() -> int:
    npm = shutil.which("npm")
    if not npm:
        print("npm was not found on PATH.", file=sys.stderr)
        return 1

    # `apiBaseUrl: ""` is deliberate: API calls resolve relative to the same
    # FC host and browser cookies are first-party.  Never substitute localhost.
    runtime_config = FRONTEND_DIR / "public" / "runtime-config.js"
    runtime_text = runtime_config.read_text(encoding="utf-8")
    if 'apiBaseUrl: ""' not in runtime_text and '"apiBaseUrl":""' not in runtime_text:
        print(
            "The FC single-origin build requires an empty runtime apiBaseUrl. "
            "Restore frontend/public/runtime-config.js before building.",
            file=sys.stderr,
        )
        return 1

    print("Building static frontend for same-origin Function Compute serving...")
    completed = subprocess.run([npm, "run", "build"], cwd=FRONTEND_DIR)
    if completed.returncode:
        return completed.returncode
    missing = [name for name in REQUIRED_FILES if not (FRONTEND_OUT / name).is_file()]
    if missing:
        print("Static export is incomplete: " + ", ".join(missing), file=sys.stderr)
        return 1

    _assert_safe_target(STATIC_TARGET)
    if STATIC_TARGET.exists():
        shutil.rmtree(STATIC_TARGET)
    shutil.copytree(FRONTEND_OUT, STATIC_TARGET)
    print(f"Bundled static release into {STATIC_TARGET.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
