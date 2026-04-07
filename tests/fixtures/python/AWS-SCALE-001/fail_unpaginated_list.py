"""Fixture for AWS-SCALE-001: list_/describe_ called directly instead of via paginator."""

import boto3

client = boto3.client("s3")


def all_buckets():
    return client.list_buckets()


def all_objects(bucket):
    return client.list_objects_v2(Bucket=bucket)
