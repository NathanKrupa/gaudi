"""Fixture for STRUCT-001: 7 models is below the >= 8 threshold."""

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
