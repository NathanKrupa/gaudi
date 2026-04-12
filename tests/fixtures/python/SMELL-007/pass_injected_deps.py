"""Fixture for SMELL-007: coordinator class with injected dependencies.

A class whose __init__ injects dependencies (self.x = x) and whose
methods access disjoint subsets of those dependencies is an orchestrator,
not a case of divergent change. The disjoint attribute sets come from
coordinating different services, not from unrelated internal state.
"""


class OrderPipeline:
    def __init__(self, validator, pricer, inventory, notifications):
        self.validator = validator
        self.pricer = pricer
        self.inventory = inventory
        self.notifications = notifications

    def validate(self, order):
        return self.validator.check(order)

    def price(self, order):
        return self.pricer.calculate(order)

    def reserve(self, order):
        return self.inventory.reserve(order)

    def notify(self, order):
        return self.notifications.send(order)
