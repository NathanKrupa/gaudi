"""Fixture: Speculative Generality."""

from abc import ABC, abstractmethod


class AbstractProcessor(ABC):
    @abstractmethod
    def process(self, data):
        pass

    @abstractmethod
    def validate(self, data):
        pass


class OnlyProcessor(AbstractProcessor):
    def process(self, data):
        return data

    def validate(self, data):
        return True


def do_work(data, logger=None, callback=None, extra=None):
    return data
