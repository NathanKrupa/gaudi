"""Fixture for STRUCT-001: a single file with 8 Django models (>= MAX_MODELS_PER_FILE)."""

from django.db import models


class Order(models.Model):
    name = models.CharField(max_length=200)


class Customer(models.Model):
    name = models.CharField(max_length=200)


class Product(models.Model):
    name = models.CharField(max_length=200)


class Invoice(models.Model):
    name = models.CharField(max_length=200)


class Address(models.Model):
    name = models.CharField(max_length=200)


class Tag(models.Model):
    name = models.CharField(max_length=200)


class Category(models.Model):
    name = models.CharField(max_length=200)


class Shipment(models.Model):
    name = models.CharField(max_length=200)
