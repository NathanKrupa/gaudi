"""
Sample Django models file with deliberate architectural issues for testing.

This is what a real project might look like before Gaudí catches the problems.
"""

from django.db import models


class Donor(models.Model):
    """A donor with too many fields crammed into one model."""

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.CharField(max_length=255)  # No index on a lookup field!
    phone = models.CharField(max_length=20, null=True)
    address_line_1 = models.CharField(max_length=255, null=True)
    address_line_2 = models.CharField(max_length=255, null=True)
    city = models.CharField(max_length=100, null=True)
    state = models.CharField(max_length=50, null=True)
    zip_code = models.CharField(max_length=20, null=True)
    country = models.CharField(max_length=100, null=True)
    employer = models.CharField(max_length=255, null=True)
    occupation = models.CharField(max_length=255, null=True)
    notes = models.TextField(null=True)
    source = models.CharField(max_length=100, null=True)
    status = models.TextField(max_length=20)  # TextField for a short status field
    giving_level = models.CharField(max_length=50, null=True)
    preferred_contact = models.CharField(max_length=50, null=True)

    class Meta:
        ordering = ["-id"]


class Gift(models.Model):
    """A gift/donation record."""

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gift_date = models.DateField()  # No index on a date field
    campaign = models.ForeignKey("Campaign", on_delete=models.SET_NULL, null=True)
    fund = models.ForeignKey("Fund", on_delete=models.SET_NULL, null=True)
    appeal = models.ForeignKey("Appeal", on_delete=models.SET_NULL, null=True)
    payment_method = models.CharField(max_length=50, null=True)
    check_number = models.CharField(max_length=50, null=True)
    receipt_sent = models.BooleanField(default=False)
    acknowledgment_sent = models.BooleanField(default=False)
    notes = models.TextField(null=True)


class Campaign(models.Model):
    """A fundraising campaign."""

    name = models.TextField()  # TextField for a name — should be CharField
    description = models.TextField(null=True)
    start_date = models.DateField(null=True)
    end_date = models.DateField(null=True)
    goal_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    status = models.CharField(max_length=20)


class Fund(models.Model):
    """A fund/designation."""

    code = models.CharField(max_length=20)  # No index on a code field
    name = models.CharField(max_length=255)
    description = models.TextField(null=True)
    is_active = models.BooleanField(default=True)


class Appeal(models.Model):
    """A solicitation appeal."""

    code = models.CharField(max_length=20)
    name = models.CharField(max_length=255)
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE)
    mail_date = models.DateField(null=True)


class Event(models.Model):
    """An event."""

    title = models.TextField()  # TextField for a title
    event_date = models.DateTimeField()
    location = models.CharField(max_length=255, null=True)
    capacity = models.IntegerField(null=True)
    registration_deadline = models.DateTimeField(null=True)


class Volunteer(models.Model):
    """A volunteer record."""

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE, null=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.CharField(max_length=255)
    skills = models.TextField(null=True)
    availability = models.TextField(null=True)


class Communication(models.Model):
    """A communication log entry."""

    donor = models.ForeignKey(Donor, on_delete=models.CASCADE)
    comm_type = models.CharField(max_length=50)
    subject = models.CharField(max_length=255, null=True)
    body = models.TextField(null=True)
    sent_date = models.DateTimeField(null=True)
    status = models.CharField(max_length=20)


class Relationship(models.Model):
    """A relationship between donors."""

    donor_a = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="relationships_a")
    donor_b = models.ForeignKey(Donor, on_delete=models.CASCADE, related_name="relationships_b")
    relationship_type = models.CharField(max_length=50)
    notes = models.TextField(null=True)
