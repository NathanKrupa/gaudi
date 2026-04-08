"""Fixture for ASYNC-002: aiohttp.ClientSession used inside async with."""

import aiohttp


async def fetch(url):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.text()
