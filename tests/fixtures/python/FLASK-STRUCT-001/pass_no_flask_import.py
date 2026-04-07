"""Fixture for FLASK-STRUCT-001: a module-level `app = Foo()` in a non-Flask file is irrelevant."""


class App:
    def run(self) -> None:
        pass


app = App()
