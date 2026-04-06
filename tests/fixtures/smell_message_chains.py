"""Fixture: Message Chains."""


class Report:
    def get_title(self):
        return self.context.document.metadata.title.value

    def get_author_email(self):
        return self.app.config.auth.provider.user.email

    def get_name(self):
        return self.user.name
