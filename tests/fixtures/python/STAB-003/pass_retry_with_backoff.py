"""Fixture for STAB-003: tenacity uses wait=, urllib3 uses backoff_factor=."""

from tenacity import retry, stop_after_attempt, wait_exponential
from urllib3.util.retry import Retry


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10), reraise=True)
def fetch():
    return 42


def make_retry_policy():
    return Retry(
        total=5,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503],
        allowed_methods=["GET"],
    )
