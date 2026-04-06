"""Fixture: Long Parameter List."""


def create_user(
    first_name, last_name, email, phone, address, city, state, zip_code, country, is_active=True
):
    return {"name": f"{first_name} {last_name}", "email": email}


def send_email(
    to,
    subject,
    body,
    cc=None,
    bcc=None,
    reply_to=None,
    is_html=False,
    track_opens=False,
    track_clicks=False,
):
    pass


def simple_add(a, b):
    return a + b
