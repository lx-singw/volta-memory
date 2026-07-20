#!/usr/bin/env python3
"""Verify the OSS/CDN -> API Gateway public edge without mutating user data."""

from __future__ import annotations

import json
import argparse
import os
import re
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen


LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}
API_PATTERN = re.compile(r'"apiBaseUrl":"([^"]+)"')


def origin(name: str) -> str:
    value = os.environ.get(name, "").strip().rstrip("/")
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc or (parsed.hostname or "").lower() in LOCAL_HOSTS:
        raise ValueError(f"{name} must be a non-local HTTPS origin.")
    return value


def request(url: str, *, method: str = "GET", headers: dict[str, str] | None = None) -> tuple[int, dict[str, str], bytes]:
    req = Request(url, method=method, headers=headers or {})
    try:
        with urlopen(req, timeout=20) as response:  # nosec B310: release URL is operator-controlled
            return response.status, dict(response.headers.items()), response.read()
    except HTTPError as exc:
        return exc.code, dict(exc.headers.items()), exc.read()
    except URLError as exc:
        raise RuntimeError(f"Could not reach {url}: {exc.reason}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-only",
        action="store_true",
        help="Validate the API Gateway domain and credentialed CORS before first CDN publication.",
    )
    args = parser.parse_args()
    try:
        app_origin = origin("VOLTA_PUBLIC_APP_ORIGIN")
        api_origin = origin("VOLTA_PUBLIC_API_BASE_URL")
        health_url = os.environ.get("VOLTA_PUBLIC_HEALTH_URL", f"{api_origin}/health").strip()
        if health_url.rstrip("/") != f"{api_origin}/health":
            raise ValueError("VOLTA_PUBLIC_HEALTH_URL must be the API Gateway /health route.")
    except ValueError as exc:
        print(f"Edge preflight failed: {exc}", file=sys.stderr)
        return 2

    try:
        health_status, _, health_body = request(health_url)
        cors_checks = [
            (
                "session end",
                *request(
                    api_origin + "/v1/me/profile",
                    method="OPTIONS",
                    headers={
                        "Origin": app_origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "content-type,x-csrf-token,idempotency-key",
                    },
                ),
            ),
            (
                "workspace deletion",
                *request(
                    api_origin + "/v1/me",
                    method="OPTIONS",
                    headers={
                        "Origin": app_origin,
                        "Access-Control-Request-Method": "DELETE",
                        "Access-Control-Request-Headers": "x-csrf-token",
                    },
                ),
            ),
        ]
    except RuntimeError as exc:
        print(f"Edge preflight failed: {exc}", file=sys.stderr)
        return 1

    failures: list[str] = []
    if not args.api_only:
        try:
            app_checks = [(route, request(app_origin + route)[0]) for route in ("/", "/try/", "/showcase/", "/memory/", "/auth/verify/")]
            config_status, _, config_body = request(app_origin + "/runtime-config.js")
        except RuntimeError as exc:
            print(f"Edge preflight failed: {exc}", file=sys.stderr)
            return 1
        for route, app_status in app_checks:
            if app_status != 200:
                failures.append(f"app route {route} returned HTTP {app_status}")
        if config_status != 200:
            failures.append(f"runtime-config.js returned HTTP {config_status}")
        config_text = config_body.decode("utf-8", errors="replace")
        api_match = API_PATTERN.search(config_text)
        if not api_match or api_match.group(1).rstrip("/") != api_origin:
            failures.append("runtime-config.js does not name the required API Gateway origin")
    if health_status != 200:
        failures.append(f"health returned HTTP {health_status}")
    else:
        try:
            if json.loads(health_body.decode("utf-8")).get("status") != "ok":
                failures.append("health did not report status=ok")
        except (UnicodeDecodeError, json.JSONDecodeError):
            failures.append("health response was not valid JSON")
    for name, cors_status, cors_headers, _cors_body in cors_checks:
        if cors_status not in {200, 204}:
            failures.append(f"{name} CORS preflight returned HTTP {cors_status}")
        if cors_headers.get("Access-Control-Allow-Origin") != app_origin:
            failures.append(f"{name} CORS did not echo the exact app origin")
        if cors_headers.get("Access-Control-Allow-Credentials", "").lower() != "true":
            failures.append(f"{name} credentialed CORS is not enabled for the app origin")
        allowed_methods = cors_headers.get("Access-Control-Allow-Methods", "").lower()
        if name == "workspace deletion" and "delete" not in allowed_methods:
            failures.append("workspace deletion CORS does not allow DELETE")
        allowed_headers = cors_headers.get("Access-Control-Allow-Headers", "").lower()
        required_headers = {"x-csrf-token"}
        if name == "session end":
            required_headers.add("idempotency-key")
        if not required_headers.issubset({value.strip() for value in allowed_headers.split(",")}):
            failures.append(f"{name} CORS omits required request headers")

    if failures:
        print("Edge preflight failed:\n- " + "\n- ".join(failures), file=sys.stderr)
        return 1
    scope = "API Gateway" if args.api_only else "public edge"
    print(f"{scope} preflight passed: {app_origin} -> {api_origin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
