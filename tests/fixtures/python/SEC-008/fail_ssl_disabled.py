"""Fixture for SEC-008: SSL verification disabled via verify=False and ssl.CERT_NONE."""

import ssl
import requests
import httpx


def fetch_without_verify(url: str) -> str:
    return requests.get(url, verify=False).text


def post_without_verify(url: str, payload: dict) -> str:
    return requests.post(url, json=payload, verify=False).text


def httpx_without_verify(url: str) -> str:
    return httpx.get(url, verify=False).text


def build_insecure_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx
