"""Fixture: Mysterious Name."""


def calculate_annual_revenue(transactions):
    x = 0
    d = {}
    for t in transactions:
        a = t["amount"]
        x += a
        d[t["year"]] = d.get(t["year"], 0) + a
    return x, d


class Processor:
    def __init__(self):
        self.d = []
        self.x = 0
        self.temp = None

    def do_stuff(self, data):
        for i in data:
            self.x += i
        return self.x


def well_named_function(user_count, threshold):
    return user_count > threshold
