# Fixture for STAB-001: UnboundedResultSet
from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=200)

# BAD: unbounded .all()
def get_all_articles():
    return Article.objects.all()

# BAD: unbounded .filter()
def get_published():
    return Article.objects.filter(published=True)

# GOOD: sliced result
def get_recent():
    return Article.objects.all()[:10]

# GOOD: .first() bounds the result
def get_one():
    return Article.objects.filter(featured=True).first()
