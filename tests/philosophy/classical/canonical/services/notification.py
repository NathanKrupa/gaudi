"""
The notification service: records an outbound notification for an order outcome.

Notification delivery — email, SMS, push, queue — is infrastructure
concern. This service depends on a ``NotificationSender`` Protocol,
and the in-memory sender used in tests simply appends to a list so
assertions can verify the pipeline spoke to its notification collaborator.
"""

from __future__ import annotations

from typing import Protocol

from ..domain.models import OrderOutcome


class NotificationSender(Protocol):
    """Delivers a notification about an order outcome to its recipient."""

    def send(self, outcome: OrderOutcome) -> None: ...


class InMemoryNotificationSender:
    """A notification sender that records every outcome for test inspection."""

    def __init__(self) -> None:
        self.sent: list[OrderOutcome] = []

    def send(self, outcome: OrderOutcome) -> None:
        self.sent.append(outcome)


class NotificationService:
    """Delegates order-outcome notification to the configured sender."""

    def __init__(self, sender: NotificationSender) -> None:
        self._sender = sender

    def notify(self, outcome: OrderOutcome) -> None:
        self._sender.send(outcome)
