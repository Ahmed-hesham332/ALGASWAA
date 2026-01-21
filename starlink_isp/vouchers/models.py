from django.db import models
from django.conf import settings
from offers.models import Offer
from servers.models import Server


class VoucherBatch(models.Model):
    reseller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    distributer = models.ForeignKey(
        "distributers.Distributer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True, blank=True)

    name = models.CharField(max_length=100)
    quantity = models.PositiveIntegerField()

    prefix = models.CharField(max_length=10, blank=True, default="")
    serial_length = models.PositiveIntegerField(default=8)
    serial_type = models.CharField(
        max_length=20,
        choices=[("numeric", "أرقام فقط"), ("alphanumeric", "أحرف وأرقام")],
        default="numeric"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)


class Voucher(models.Model):
    STATUS_CHOICES = [
    ("unused", "غير مستخدم"),
    ("used", "مستخدم"),
    ("expired", "منتهي"),
    ]
    batch = models.ForeignKey(VoucherBatch, on_delete=models.SET_NULL, null=True, blank=True, related_name="vouchers")
    server = models.ForeignKey(Server, on_delete=models.CASCADE)
    offer = models.ForeignKey(Offer, on_delete=models.SET_NULL, null=True, blank=True)

    serial = models.CharField(max_length=50, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    is_used = models.CharField(max_length=10, choices=STATUS_CHOICES, default="unused")
    usage_mb = models.FloatField(default=0)
    mac_address = models.CharField(max_length=50, blank=True)
    ip_address = models.CharField(max_length=50, blank=True)
    token = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return self.serial

