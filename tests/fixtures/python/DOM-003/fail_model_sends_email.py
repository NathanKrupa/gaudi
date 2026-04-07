# Fixture for DOM-003: model whose method sends email directly.
from django.core.mail import send_mail
from django.db import models


class User(models.Model):
    email = models.EmailField()
    name = models.CharField(max_length=200)

    def notify_signup(self):
        send_mail(
            subject="Welcome",
            message=f"Hi {self.name}",
            from_email="noreply@example.com",
            recipient_list=[self.email],
        )
