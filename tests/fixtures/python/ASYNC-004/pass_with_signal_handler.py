"""Fixture for ASYNC-004: asyncio.run with a signal handler registered."""

import asyncio
import signal


def shutdown(signum, frame):
    raise SystemExit(0)


signal.signal(signal.SIGTERM, shutdown)


async def serve():
    while True:
        await asyncio.sleep(1)


asyncio.run(serve())
