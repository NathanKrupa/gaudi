# Negative fixture for CPLX-002: every parameter is used directly, none threaded


def compute(x, y):
    return x * 2 + y * 3


def render(user):
    return user.name.upper()


def main(config):
    enabled = config["enabled"]
    return enabled
