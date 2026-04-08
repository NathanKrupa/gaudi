"""Fixture for DJ-ARCH-002: a thin signal handler that just updates a counter."""

from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=object)
def bump_counter(sender, instance, created, **kwargs):
    if created:
        instance.account.order_count += 1
        instance.account.save(update_fields=["order_count"])
