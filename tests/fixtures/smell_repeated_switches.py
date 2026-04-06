"""Fixture: Repeated Switches."""


def get_price(animal_type):
    if animal_type == "dog":
        return 50
    elif animal_type == "cat":
        return 30
    elif animal_type == "bird":
        return 20
    return 0


def get_food(animal_type):
    if animal_type == "dog":
        return "kibble"
    elif animal_type == "cat":
        return "fish"
    elif animal_type == "bird":
        return "seeds"
    return "generic"


def get_sound(animal_type):
    if animal_type == "dog":
        return "woof"
    elif animal_type == "cat":
        return "meow"
    elif animal_type == "bird":
        return "tweet"
    return "..."
