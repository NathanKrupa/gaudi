# Fixture for STAB-005: BlockingInAsync
import asyncio
import time
import requests

# BAD: time.sleep in async function
async def poll_status():
    time.sleep(5)
    return "done"

# BAD: requests.get in async function
async def fetch_data(url):
    return requests.get(url, timeout=10)

# GOOD: asyncio.sleep is non-blocking
async def async_poll():
    await asyncio.sleep(5)
    return "done"

# GOOD: blocking call in sync function is fine
def sync_fetch(url):
    return requests.get(url, timeout=10)
