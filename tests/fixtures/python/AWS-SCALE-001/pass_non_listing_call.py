"""Fixture for AWS-SCALE-001: a non-listing API call (put_object) is out of scope."""

import boto3

client = boto3.client("s3")


def upload(key, body):
    return client.put_object(Bucket="my-bucket", Key=key, Body=body)
