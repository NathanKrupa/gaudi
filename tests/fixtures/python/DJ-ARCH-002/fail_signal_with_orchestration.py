"""Fixture for DJ-ARCH-002: post_save signal handler doing real orchestration."""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
import requests


@receiver(post_save, sender=object)
def order_post_save(sender, instance, created, **kwargs):
    if created:
        send_mail("New order", "thanks", "noreply@x.com", [instance.email])
    if instance.total > 100:
        requests.post("https://hooks.example.com/big-order", json={"id": instance.id})
    if instance.is_paid:
        instance.fulfillment.start()
