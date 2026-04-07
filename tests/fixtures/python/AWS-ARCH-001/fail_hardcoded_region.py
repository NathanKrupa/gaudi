"""Fixture for AWS-ARCH-001: boto3 client built with a literal region_name."""

import boto3

client = boto3.client("s3", region_name="us-east-1")
