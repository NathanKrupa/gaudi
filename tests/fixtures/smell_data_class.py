"""Fixture: Data Class."""


class Point:
    def __init__(self, x, y):
        self.x = x
        self.y = y


class UserDTO:
    def __init__(self, name, email, age):
        self.name = name
        self.email = email
        self.age = age

    def __repr__(self):
        return f"UserDTO({self.name})"


class ActiveRecord:
    def __init__(self, name):
        self.name = name

    def save(self):
        pass

    def validate(self):
        pass
