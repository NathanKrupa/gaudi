# Fixture for DOM-001: telemetry/event tables are anemic by design.
# MatchImpression records an observation; behavior belongs to the aggregator.
from django.db import models


class MatchImpression(models.Model):
    match_id = models.IntegerField()
    user_id = models.IntegerField()
    shown_at = models.DateTimeField()
    position = models.IntegerField()
    surface = models.CharField(max_length=50)
    dwell_ms = models.IntegerField()


class Feedback(models.Model):
    user_id = models.IntegerField()
    target_id = models.IntegerField()
    rating = models.IntegerField()
    comment = models.CharField(max_length=500)
    created_at = models.DateTimeField()
    source = models.CharField(max_length=50)
