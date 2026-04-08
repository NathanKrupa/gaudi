"""Fixture for SMELL-004: 7 positional params exceeds the > 6 threshold."""


def build_user(name, email, age, address, phone, role, department):
    return {
        "name": name,
        "email": email,
        "age": age,
        "address": address,
        "phone": phone,
        "role": role,
        "department": department,
    }
