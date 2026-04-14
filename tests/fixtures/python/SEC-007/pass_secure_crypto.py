"""Passing fixture for SEC-007: strong hashes and secrets module for tokens."""

import hashlib
import secrets


def hash_password(password: str, salt: bytes) -> bytes:
    return hashlib.sha256(password.encode() + salt).digest()


def hash_password_scrypt(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)


def generate_session_token() -> str:
    return secrets.token_hex(16)


def generate_api_key() -> str:
    return secrets.token_urlsafe(32)
