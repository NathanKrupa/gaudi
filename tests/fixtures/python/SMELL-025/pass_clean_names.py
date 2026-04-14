# ABOUTME: Fixture for SMELL-025 — clean names with no temporal markers.
# ABOUTME: These should NOT trigger the rule.


class AuthClient:
    def connect(self):
        pass


def send_billing(request):
    return request


class UserService:
    def get_user(self):
        pass


TIMEOUT = 30
