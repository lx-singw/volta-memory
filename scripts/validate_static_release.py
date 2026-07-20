#!/usr/bin/env python3
"""Fail a static release that can call localhost or lacks runtime API config."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCALHOST_PATTERN = re.compile(
    r"https?://(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?::\d+)?", re.IGNORECASE
)
API_ORIGIN_PATTERN = re.compile(r'"apiBaseUrl":"([^"]*)"')


def validate_out_dir(out_dir: Path) -> int:
    out_dir = out_dir.resolve()
    if not out_dir.is_dir():
        print(f"Release validation failed: static export directory does not exist: {out_dir}", file=sys.stderr)
        return 2

    runtime_config = out_dir / "runtime-config.js"
    if not runtime_config.is_file():
        print("Release validation failed: runtime-config.js was not exported.", file=sys.stderr)
        return 2
    runtime_text = runtime_config.read_text(encoding="utf-8")
    api_match = API_ORIGIN_PATTERN.search(runtime_text)
    if not api_match:
        print("Release validation failed: runtime-config.js has no apiBaseUrl value.", file=sys.stderr)
        return 2
    parsed = urlparse(api_match.group(1))
    if parsed.scheme != "https" or not parsed.netloc or LOCALHOST_PATTERN.search(api_match.group(1)):
        print("Release validation failed: apiBaseUrl must be a non-local HTTPS origin.", file=sys.stderr)
        return 2

    # `trailingSlash: true` is a release invariant: OSS/CDN can resolve these
    # directory indexes without relying on a catch-all error rewrite.
    required_pages = ("index.html", "try/index.html", "showcase/index.html", "memory/index.html", "auth/verify/index.html")
    missing_pages = [page for page in required_pages if not (out_dir / page).is_file()]
    if missing_pages:
        print(
            "Release validation failed: extensionless route indexes are missing:\n"
            + "\n".join(f"  - /{page}" for page in missing_pages),
            file=sys.stderr,
        )
        return 2

    offending_files: list[Path] = []
    for path in out_dir.rglob("*"):
        if path.suffix.lower() not in {".html", ".js", ".json"}:
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if LOCALHOST_PATTERN.search(content):
            offending_files.append(path.relative_to(out_dir))

    if offending_files:
        print(
            "Release validation failed: localhost API references found in static output:\n"
            + "\n".join(f"  - {path}" for path in offending_files),
            file=sys.stderr,
        )
        return 2

    print(f"Static release validation passed for {out_dir} -> {api_match.group(1)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "frontend" / "out")
    args = parser.parse_args()
    return validate_out_dir(args.out_dir)


if __name__ == "__main__":
    raise SystemExit(main())
