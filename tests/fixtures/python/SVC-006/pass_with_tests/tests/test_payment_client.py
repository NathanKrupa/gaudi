"""Contract test for the payment client."""

from unittest.mock import patch

from src.clients.payment_client import charge


def test_charge_returns_payload():
    with patch("src.clients.payment_client.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"status": "ok"}
        assert charge("cust-1", 100) == {"status": "ok"}
