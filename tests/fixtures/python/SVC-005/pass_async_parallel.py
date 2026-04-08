"""Fixture for SVC-005: async parallel fan-out is the recommended shape."""

import asyncio

import httpx


async def fetch_user_dashboard(user_id):
    async with httpx.AsyncClient() as client:
        profile, invoices = await asyncio.gather(
            client.get(f"https://users.example.com/api/{user_id}"),
            client.get(f"https://billing.example.com/api/{user_id}"),
        )
    return profile.json(), invoices.json()
