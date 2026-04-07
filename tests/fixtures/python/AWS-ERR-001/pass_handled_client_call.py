"""Fixture for AWS-ERR-001: API call wrapped in try/except for ClientError."""

import boto3
from botocore.exceptions import ClientError

client = boto3.client("s3")


def upload(key, body):
    try:
        client.put_object(Bucket="my-bucket", Key=key, Body=body)
    except ClientError:
        return None
    return key
