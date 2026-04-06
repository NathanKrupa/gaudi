"""Fixture: Divergent Change."""


class Employee:
    def __init__(self, name, salary, department, email):
        self.name = name
        self.salary = salary
        self.department = department
        self.email = email
        self.notifications = []
        self.pay_history = []

    def calculate_pay(self):
        return self.salary * 1.1

    def add_bonus(self, amount):
        self.salary += amount
        self.pay_history.append(amount)

    def send_notification(self, msg):
        self.notifications.append(msg)
        self.email_body = f"To: {self.email}\n{msg}"

    def format_notification(self):
        return "\n".join(self.notifications)
