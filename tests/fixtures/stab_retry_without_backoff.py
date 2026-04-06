# Fixture for STAB-003: RetryWithoutBackoff
from tenacity import retry, stop_after_attempt
from urllib3.util import Retry

# BAD: tenacity retry without wait parameter
@retry(stop=stop_after_attempt(3), reraise=True)
def call_api():
    pass

# BAD: urllib3 Retry without backoff_factor
session_retry = Retry(total=3, status_forcelist=[500, 502])

# GOOD: tenacity with wait
@retry(stop=stop_after_attempt(3), wait=2)
def call_api_with_wait():
    pass

# GOOD: urllib3 with backoff
good_retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500])
