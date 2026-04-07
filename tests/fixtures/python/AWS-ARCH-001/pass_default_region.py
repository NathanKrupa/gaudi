"""Fixture for AWS-ARCH-001: no region passed at all -- default chain takes over."""

import boto3

client = boto3.client("s3")
