"""Fixture for STAB-005: asyncio.sleep and httpx.AsyncClient are non-blocking."""

import asyncio

import httpx


async def fetch(url):
    await asyncio.sleep(1)
    async with httpx.AsyncClient() as client:
        return await client.get(url)
