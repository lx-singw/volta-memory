#!/usr/bin/env python3
"""Deploy the zero-domain, same-origin Function Compute hackathon release.

This command deliberately does not create paid resources, provision a custom
domain, or run the long Qwen benchmark.  It performs the minimum honest demo
release: migration, static bundle, FC deployment, and public health smoke.
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from urllib.parse import urlparse

import httpx
from dotenv import dotenv_values


REPO_ROOT = Path(__file__).resolve().parents[1]
DEPENDENCY_ARCHIVE = REPO_ROOT / "deployment" / "artifacts" / "volta-memory-fc-python310-deps.tar.gz"


def normalise_origin(value: str) -> str:
    origin = value.strip().rstrip("/")
    parsed = urlparse(origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"}:
        raise ValueError("--function-origin must be an HTTPS origin, for example https://<function>.fcapp.run")
    return origin


def run(command: list[str], *, environment: dict[str, str]) -> None:
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=REPO_ROOT, env=environment)
    if result.returncode:
        raise RuntimeError(f"Command failed with exit code {result.returncode}: {' '.join(command)}")


def restore_dependency_bundle() -> None:
    """Restore the versioned Linux dependency bundle when cloning for release."""
    dependency_root = REPO_ROOT / "backend" / "python"
    if (dependency_root / "fastapi").is_dir():
        return
    if not DEPENDENCY_ARCHIVE.is_file():
        raise RuntimeError(
            "backend/python and the versioned Function Compute dependency archive are both missing. "
            "Restore Docker Hub connectivity and rerun with --build-fc."
        )

    backend_root = (REPO_ROOT / "backend").resolve()
    dependency_root = dependency_root.resolve()
    print(f"Restoring Linux Function Compute dependencies from {DEPENDENCY_ARCHIVE.relative_to(REPO_ROOT)}")
    with tarfile.open(DEPENDENCY_ARCHIVE, "r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            destination = (backend_root / member.name).resolve()
            if (
                member.issym()
                or member.islnk()
                or (destination != dependency_root and dependency_root not in destination.parents)
            ):
                raise RuntimeError("Dependency archive contains an unsafe path.")
        archive.extractall(backend_root, members=members)

    if not (dependency_root / "fastapi").is_dir():
        raise RuntimeError("Dependency archive did not contain the expected FastAPI runtime bundle.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--function-origin", required=True)
    parser.add_argument("--skip-migrations", action="store_true")
    parser.add_argument(
        "--build-fc",
        action="store_true",
        help="Rebuild the Linux dependency bundle with Serverless Devs before deployment.",
    )
    args = parser.parse_args()

    try:
        function_origin = normalise_origin(args.function_origin)
    except ValueError as exc:
        print(f"Release configuration error: {exc}", file=sys.stderr)
        return 2

    env_file = REPO_ROOT / ".env"
    if not env_file.is_file():
        print("Release configuration error: .env is required locally.", file=sys.stderr)
        return 2
    environment = os.environ.copy()
    environment.update({key: value for key, value in dotenv_values(env_file).items() if value is not None})
    missing = [name for name in ("DATABASE_URL", "QWEN_API_KEY") if not environment.get(name)]
    if missing:
        print("Release configuration error: missing " + ", ".join(missing), file=sys.stderr)
        return 2

    # The demo remains secure enough for a public judging link without making
    # the user paste new secrets into source control.  Persist these in Secret
    # Manager before switching to the custom-domain production topology.
    environment.setdefault("AUTH_SESSION_SECRET", secrets.token_urlsafe(48))
    environment.setdefault("ADMIN_API_KEY", secrets.token_urlsafe(32))
    environment.setdefault("AUTH_SESSION_COOKIE_NAME", "volta_session")
    environment.setdefault("AUTH_CSRF_COOKIE_NAME", "volta_csrf")
    environment.setdefault("AUTH_SESSION_TTL_HOURS", "336")
    environment.setdefault("AUTH_EMAIL_WEBHOOK_URL", "")
    environment.setdefault("AUTH_EMAIL_WEBHOOK_TOKEN", "")
    environment.update(
        {
            "APP_ENV": "production",
            "CORS_ALLOWED_ORIGINS": function_origin,
            "SERVE_BUNDLED_STATIC": "true",
            "AUTH_COOKIE_DOMAIN": "",
            "AUTH_MAGIC_LINK_BASE_URL": function_origin,
            "AUTH_EMAIL_PROVIDER": "disabled",
            "VOLTA_PUBLIC_APP_ORIGIN": function_origin,
            "VOLTA_PUBLIC_API_BASE_URL": function_origin,
            "VOLTA_PUBLIC_HEALTH_URL": f"{function_origin}/health",
        }
    )

    serverless = environment.get("SERVERLESS_DEVS_BIN") or shutil.which("s") or "/home/lx_singw/.npm-global/bin/s"
    if not Path(serverless).exists() and not shutil.which(serverless):
        print("Release configuration error: Serverless Devs CLI 's' was not found.", file=sys.stderr)
        return 2

    try:
        if not args.skip_migrations:
            run(["bash", "migrate.sh"], environment=environment)
        run([sys.executable, "scripts/build_fc_single_origin_release.py"], environment=environment)
        # The versioned Linux bundle was created by the FC Docker build. It
        # makes a Cloud Shell release reproducible even when Docker Hub is not
        # reachable; use --build-fc only to refresh it.
        dependency_marker = REPO_ROOT / "backend" / "python" / "fastapi"
        if args.build_fc:
            run([serverless, "-t", "s.single-origin.yaml", "build", "--use-docker"], environment=environment)
        elif not dependency_marker.is_dir():
            restore_dependency_bundle()
        # Serverless Devs otherwise echoes environment-variable diffs, which
        # can expose deployed secrets in terminal recordings or CI logs.
        run([serverless, "--silent", "-t", "s.single-origin.yaml", "deploy", "-y"], environment=environment)
        response = httpx.get(f"{function_origin}/health", timeout=20)
        response.raise_for_status()
        if response.json().get("status") != "ok":
            raise RuntimeError("Public health endpoint did not return status=ok.")
    except (RuntimeError, subprocess.SubprocessError, httpx.HTTPError) as exc:
        print(f"Single-origin FC release failed: {exc}", file=sys.stderr)
        return 1

    print(f"Single-origin Alibaba demo release is live at {function_origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
