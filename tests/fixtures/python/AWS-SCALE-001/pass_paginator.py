"""Fixture for AWS-SCALE-001: paginator covers the result set."""

import boto3

client = boto3.client("s3")


def all_objects(bucket):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket):
        yield from page.get("Contents", [])
