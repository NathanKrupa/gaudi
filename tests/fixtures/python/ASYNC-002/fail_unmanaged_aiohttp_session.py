"""Fixture for ASYNC-002: aiohttp.ClientSession() created without async with."""

import aiohttp


async def fetch(url):
    session = aiohttp.ClientSession()
    response = await session.get(url)
    return await response.text()
