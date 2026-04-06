"""Fixture: Middle Man."""


class ServiceProxy:
    def __init__(self, service):
        self._service = service

    def get_user(self, uid):
        return self._service.get_user(uid)

    def save_user(self, user):
        return self._service.save_user(user)

    def delete_user(self, uid):
        return self._service.delete_user(uid)

    def list_users(self):
        return self._service.list_users()


class UsefulWrapper:
    def __init__(self, service):
        self._service = service

    def get_user(self, uid):
        user = self._service.get_user(uid)
        user["accessed"] = True
        return user

    def save_user(self, user):
        user["updated_at"] = "now"
        return self._service.save_user(user)
