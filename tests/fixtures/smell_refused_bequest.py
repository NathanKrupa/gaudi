"""Fixture: Refused Bequest."""


class BaseHandler:
    def on_start(self):
        pass

    def on_finish(self):
        pass

    def process(self):
        pass


class LimitedHandler(BaseHandler):
    def on_start(self):
        print("starting")

    def on_finish(self):
        raise NotImplementedError("not supported")

    def process(self):
        pass


class GoodHandler(BaseHandler):
    def on_start(self):
        print("starting")

    def on_finish(self):
        print("finishing")

    def process(self):
        print("processing")
