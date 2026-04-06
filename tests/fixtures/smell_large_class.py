"""Fixture: Large Class."""


class GodObject:
    def __init__(self):
        self.name = ""
        self.email = ""
        self.phone = ""
        self.address = ""
        self.city = ""
        self.state = ""

    def validate_name(self):
        pass

    def validate_email(self):
        pass

    def validate_phone(self):
        pass

    def save(self):
        pass

    def delete(self):
        pass

    def to_dict(self):
        pass

    def from_dict(self, d):
        pass

    def send_email(self):
        pass

    def format_address(self):
        pass

    def calculate_score(self):
        pass

    def export_csv(self):
        pass

    def import_csv(self, path):
        pass

    def merge(self, other):
        pass


class SmallClass:
    def __init__(self):
        self.value = 0

    def get(self):
        return self.value
