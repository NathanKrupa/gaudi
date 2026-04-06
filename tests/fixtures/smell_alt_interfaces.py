"""Fixture: Alternative Classes with Different Interfaces."""


class JsonSerializer:
    def serialize(self, data):
        return str(data)

    def deserialize(self, text):
        return eval(text)


class XmlConverter:
    def convert(self, data):
        return f"<data>{data}</data>"

    def parse(self, text):
        return text


class CsvFormatter:
    def format(self, data):
        return ",".join(str(d) for d in data)

    def read(self, text):
        return text.split(",")
