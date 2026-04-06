# Fixture for STAB-004: UnboundedCache
from functools import cache, lru_cache

# BAD: @cache is always unbounded
@cache
def compute_expensive(n):
    return n ** n

# BAD: lru_cache with maxsize=None is explicitly unbounded
@lru_cache(maxsize=None)
def parse_config(path):
    return open(path).read()

# GOOD: lru_cache with default maxsize (128)
@lru_cache
def get_setting(key):
    return key.upper()

# GOOD: lru_cache with explicit bound
@lru_cache(maxsize=256)
def lookup(key):
    return key
