#!/usr/bin/env python3
"""Verify the deployed Function Compute function and public health endpoint.

This script makes a real Function Compute 3.0 SDK call. It prints only
non-sensitive deployment metadata, then checks the public API Gateway health
endpoint. Use it in the Alibaba deployment proof recording.
"""

from __future__ import annotations

import json
import os
import sys
from urllib.error import URLError
from urllib.request import urlopen


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise ValueError(f"Set {name} before running deployment verification.")
    return value


def main() -> int:
    try:
        access_key_id = required("ALIBABA_ACCESS_KEY_ID")
        access_key_secret = required("ALIBABA_ACCESS_KEY_SECRET")
        endpoint = required("ALIBABA_FC_ENDPOINT")
        function_name = required("ALIBABA_FC_FUNCTION_NAME")
        health_url = required("VOLTA_PUBLIC_HEALTH_URL")
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2

    try:
        from alibabacloud_fc20230330.client import Client as FcClient
        from alibabacloud_fc20230330 import models as fc_models
        from alibabacloud_tea_openapi import models as open_api_models
    except ImportError:
        print("Install proof dependencies with: pip install -e 'backend[alibaba]'", file=sys.stderr)
        return 2

    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        endpoint=endpoint,
    )
    try:
        response = FcClient(config).get_function(function_name, fc_models.GetFunctionRequest())
        body = response.body
    except Exception as exc:
        print(f"Function Compute verification failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    print("Function Compute SDK verification succeeded.")
    print(f"  function={getattr(body, 'function_name', function_name)}")
    print(f"  runtime={getattr(body, 'runtime', 'unknown')}")
    print(f"  state={getattr(body, 'state', 'unknown')}")
    print(f"  last_modified={getattr(body, 'last_modified_time', 'unknown')}")

    try:
        with urlopen(health_url, timeout=15) as response:  # nosec B310: release URL is explicit env input
            payload = json.loads(response.read().decode("utf-8"))
        if payload.get("status") != "ok":
            raise RuntimeError(f"unexpected health payload: {payload}")
    except (URLError, OSError, ValueError, RuntimeError) as exc:
        print(f"Public health verification failed: {type(exc).__name__}", file=sys.stderr)
        return 1

    print(f"Public API health verification succeeded: {health_url}")
    print(f"  database={payload.get('database', 'unknown')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
