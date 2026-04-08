"""Fixture for ASYNC-003: pure async module using only an async HTTP client."""

import httpx


async def fetch(url):
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.text
