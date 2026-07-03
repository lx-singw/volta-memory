#!/usr/bin/env python3
"""Proof of Alibaba Cloud deployment — calls a real Alibaba Cloud SDK method."""

from __future__ import annotations

import os
import sys


def main() -> int:
    access_key_id = os.environ.get("ALIBABA_ACCESS_KEY_ID", "")
    access_key_secret = os.environ.get("ALIBABA_ACCESS_KEY_SECRET", "")
    region = os.environ.get("ALIBABA_REGION", "ap-southeast-1")
    instance_id = os.environ.get("ALIBABA_ECS_INSTANCE_ID", "")
    rds_instance_id = os.environ.get("ALIBABA_RDS_INSTANCE_ID", "")

    if not access_key_id or not access_key_secret:
        print("Set ALIBABA_ACCESS_KEY_ID and ALIBABA_ACCESS_KEY_SECRET to run verification.")
        return 1

    try:
        from alibabacloud_ecs20140526.client import Client as EcsClient
        from alibabacloud_tea_openapi import models as open_api_models
        from alibabacloud_ecs20140526 import models as ecs_models
    except ImportError:
        print("Install Alibaba SDK: pip install -e '.[alibaba]'")
        return 1

    config = open_api_models.Config(
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        region_id=region,
    )
    client = EcsClient(config)

    request = ecs_models.DescribeInstancesRequest(region_id=region)
    if instance_id:
        request.instance_ids = f'["{instance_id}"]'

    response = client.describe_instances(request)
    instances = response.body.instances.instance or []
    print(f"Alibaba Cloud ECS API call succeeded in region {region}.")
    print(f"Instances returned: {len(instances)}")
    for inst in instances[:3]:
        print(f"  - {inst.instance_id} status={inst.status}")

    if rds_instance_id:
        print(f"Configured RDS instance id: {rds_instance_id}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
