"""Fixture for AWS-ERR-001: no boto3 client assignment in this file."""

import boto3


def helper(thing):
    return thing.put_object()  # `thing` is not a boto3 client


_ = boto3
