"""Passing fixture for SEC-008: default verification and explicit CA bundles."""

import ssl
import requests


def fetch(url: str) -> str:
    return requests.get(url).text


def fetch_with_ca_bundle(url: str, ca_path: str) -> str:
    return requests.get(url, verify=ca_path).text


def fetch_with_verify_true(url: str) -> str:
    return requests.get(url, verify=True).text


def build_secure_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.verify_mode = ssl.CERT_REQUIRED
    return ctx
