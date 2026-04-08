"""Fixture for STRUCT-012: a file with __main__ guard but no CLI library import is out of scope."""


def main():
    print("hello")  # noqa: T201


if __name__ == "__main__":
    main()
