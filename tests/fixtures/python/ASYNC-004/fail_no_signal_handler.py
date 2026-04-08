"""Fixture for ASYNC-004: asyncio.run without signal handler registration."""

import asyncio


async def serve():
    while True:
        await asyncio.sleep(1)


asyncio.run(serve())
