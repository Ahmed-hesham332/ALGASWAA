from django.db import models
from django.conf import settings

class Plan(models.Model):
    name = models.CharField(max_length=50)
    price_display = models.CharField(max_length=20)
    number_of_clients = models.IntegerField()
    number_of_servers = models.IntegerField()
    number_of_vouchers = models.IntegerField()

    def __str__(self):
        return self.name

class TechSupport(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tech_support_profile"
    )
    name = models.CharField(max_length=50, default="Tech Support")
    phone = models.CharField(max_length=20)
    bank_name = models.CharField(max_length=50)
    bank_account_number = models.CharField(max_length=50)
    bank_account_holder = models.CharField(max_length=50)

    def __str__(self):
        return self.name