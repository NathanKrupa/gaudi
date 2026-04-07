# ABOUTME: Tests for boto3 library rules (AWS-ARCH-001, AWS-ERR-001, AWS-SCALE-001).
# ABOUTME: Covers hardcoded regions, bare client calls, and unpaginated list operations.
"""Tests for boto3 library-specific rules."""

import tempfile
from pathlib import Path

from gaudi.packs.python.pack import PythonPack


def _check_source(source: str) -> list:
    """Helper: write source to a temp project with boto3 detected, return findings."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "pyproject.toml").write_text(
            '[project]\nname = "myapp"\ndependencies = ["boto3"]\n'
        )
        (root / "app.py").write_text(source)
        pack = PythonPack()
        return pack.check(root)


class TestHardcodedRegion:
    """AWS-ARCH-001: region_name hardcoded instead of config-injected."""

    def test_hardcoded_region_in_client(self):
        source = "import boto3\n\nclient = boto3.client('s3', region_name='us-east-1')\n"
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ARCH-001"]
        assert len(hits) == 1
        assert hits[0].line == 3

    def test_hardcoded_region_in_resource(self):
        source = "import boto3\n\ns3 = boto3.resource('s3', region_name='eu-west-1')\n"
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ARCH-001"]
        assert len(hits) == 1

    def test_hardcoded_region_in_session(self):
        source = "import boto3\n\nsession = boto3.Session(region_name='us-west-2')\n"
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ARCH-001"]
        assert len(hits) == 1

    def test_no_finding_when_region_from_variable(self):
        source = (
            "import boto3\n"
            "import os\n"
            "\n"
            "region = os.environ['AWS_REGION']\n"
            "client = boto3.client('s3', region_name=region)\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ARCH-001"]
        assert len(hits) == 0

    def test_no_finding_when_no_region_kwarg(self):
        source = "import boto3\n\nclient = boto3.client('s3')\n"
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ARCH-001"]
        assert len(hits) == 0


class TestBareClientCall:
    """AWS-ERR-001: boto3 client/resource call without try/except for ClientError."""

    def test_bare_client_method_call(self):
        source = (
            "import boto3\n"
            "\n"
            "def upload(bucket, key, data):\n"
            "    client = boto3.client('s3')\n"
            "    client.put_object(Bucket=bucket, Key=key, Body=data)\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ERR-001"]
        assert len(hits) == 1
        assert hits[0].line == 5

    def test_no_finding_when_wrapped_in_try(self):
        source = (
            "import boto3\n"
            "from botocore.exceptions import ClientError\n"
            "\n"
            "def upload(bucket, key, data):\n"
            "    client = boto3.client('s3')\n"
            "    try:\n"
            "        client.put_object(Bucket=bucket, Key=key, Body=data)\n"
            "    except ClientError:\n"
            "        pass\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ERR-001"]
        assert len(hits) == 0

    def test_no_finding_when_wrapped_with_base_exception(self):
        source = (
            "import boto3\n"
            "\n"
            "def upload(bucket, key, data):\n"
            "    client = boto3.client('s3')\n"
            "    try:\n"
            "        client.put_object(Bucket=bucket, Key=key, Body=data)\n"
            "    except Exception:\n"
            "        pass\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ERR-001"]
        assert len(hits) == 0

    def test_bare_resource_method_call(self):
        source = (
            "import boto3\n"
            "\n"
            "def download():\n"
            "    s3 = boto3.resource('s3')\n"
            "    s3.Bucket('my-bucket').download_file('key', '/tmp/file')\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-ERR-001"]
        assert len(hits) == 1


class TestUnpaginatedList:
    """AWS-SCALE-001: list_* operation without Paginator."""

    def test_unpaginated_list_objects(self):
        source = (
            "import boto3\n"
            "\n"
            "def list_files():\n"
            "    client = boto3.client('s3')\n"
            "    return client.list_objects_v2(Bucket='my-bucket')\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-SCALE-001"]
        assert len(hits) == 1
        assert hits[0].line == 5

    def test_unpaginated_list_buckets(self):
        source = (
            "import boto3\n"
            "\n"
            "def get_buckets():\n"
            "    client = boto3.client('s3')\n"
            "    return client.list_buckets()\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-SCALE-001"]
        assert len(hits) == 1

    def test_unpaginated_describe_instances(self):
        source = (
            "import boto3\n"
            "\n"
            "def get_instances():\n"
            "    ec2 = boto3.client('ec2')\n"
            "    return ec2.describe_instances()\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-SCALE-001"]
        assert len(hits) == 1

    def test_no_finding_for_non_list_operation(self):
        source = (
            "import boto3\n"
            "\n"
            "def get_object():\n"
            "    client = boto3.client('s3')\n"
            "    return client.get_object(Bucket='b', Key='k')\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-SCALE-001"]
        assert len(hits) == 0

    def test_no_finding_when_using_paginator(self):
        source = (
            "import boto3\n"
            "\n"
            "def list_files():\n"
            "    client = boto3.client('s3')\n"
            "    paginator = client.get_paginator('list_objects_v2')\n"
            "    for page in paginator.paginate(Bucket='my-bucket'):\n"
            "        yield from page['Contents']\n"
        )
        findings = _check_source(source)
        hits = [f for f in findings if f.code == "AWS-SCALE-001"]
        assert len(hits) == 0
