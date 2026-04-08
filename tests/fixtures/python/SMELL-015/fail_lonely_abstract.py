"""Fixture for SMELL-015: ABC with only one subclass is premature."""

from abc import ABC, abstractmethod


class Storage(ABC):
    @abstractmethod
    def save(self, item):
        ...


class FileStorage(Storage):
    def save(self, item):
        return item
