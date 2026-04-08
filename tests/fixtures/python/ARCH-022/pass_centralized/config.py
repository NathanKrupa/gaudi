import os


def load():
    return {
        "a": os.getenv("A"),
        "b": os.getenv("B"),
        "c": os.getenv("C"),
        "d": os.getenv("D"),
    }
