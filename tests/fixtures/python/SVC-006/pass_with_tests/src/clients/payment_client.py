"""External payment client with a paired contract test."""

import requests


def charge(customer_id, amount):
    response = requests.post(
        "https://payments.example.com/api/charges",
        json={"customer_id": customer_id, "amount": amount},
    )
    return response.json()
