"""Fixture for AWS-ERR-001: a boto3 API call with no try/except wrapping it."""

import boto3

client = boto3.client("s3")


def upload(key, body):
    client.put_object(Bucket="my-bucket", Key=key, Body=body)
