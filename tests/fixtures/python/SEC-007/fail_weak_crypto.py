"""Fixture for SEC-007: hashlib.md5/sha1 and random for security tokens."""

import hashlib
import random


def hash_password_md5(password: str) -> str:
    return hashlib.md5(password.encode()).hexdigest()


def hash_password_sha1(password: str) -> str:
    return hashlib.sha1(password.encode()).hexdigest()


def generate_session_token() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(16))


def generate_api_key() -> float:
    return random.random()
