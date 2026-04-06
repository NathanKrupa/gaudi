"""Fixture: Feature Envy."""


class Order:
    def __init__(self):
        self.status = "new"

    def get_customer_summary(self, customer):
        name = customer.first_name + " " + customer.last_name
        address = customer.address.street + ", " + customer.address.city
        phone = customer.phone
        email = customer.email
        return f"{name}\n{address}\n{phone}\n{email}"

    def update_status(self, new_status):
        self.status = new_status
