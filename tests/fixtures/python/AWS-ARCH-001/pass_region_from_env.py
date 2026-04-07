"""Fixture for AWS-ARCH-001: region resolved from configuration, not a literal."""

import os

import boto3

client = boto3.client("s3", region_name=os.environ["AWS_REGION"])
