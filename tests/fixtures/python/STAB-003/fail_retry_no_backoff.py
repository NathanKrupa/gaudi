"""Fixture for STAB-003: tenacity @retry without wait, urllib3 Retry without backoff_factor."""

from tenacity import retry, stop_after_attempt
from urllib3.util.retry import Retry


@retry(stop=stop_after_attempt(3), reraise=True)
def fetch():
    return 42


def make_retry_policy():
    return Retry(total=5, status_forcelist=[500, 502, 503], allowed_methods=["GET"])
