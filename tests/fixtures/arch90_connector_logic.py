"""Fixture: Connector contains business logic."""


class DatabaseConnector:
    def get_user(self, user_id):
        user = self.db.query(f"SELECT * FROM users WHERE id = {user_id}")
        # Business logic in connector — should be in service
        if user.role == "admin":
            user.permissions = ["read", "write", "delete"]
        elif user.role == "viewer":
            user.permissions = ["read"]
        else:
            user.permissions = []
        return user
