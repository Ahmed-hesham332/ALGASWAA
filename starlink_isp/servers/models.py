# servers/models.py
from django.db import models
from django.conf import settings

class Server(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="servers"
    )

    name = models.CharField(max_length=200)
    serial_number = models.CharField(null=False, blank=False, default="")
    ip_address = models.GenericIPAddressField(null=False, blank=False)
    api_password = models.CharField(max_length=200, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def connection_info(self):
        return {
            "ip": self.ip_address,
            "api_password": self.api_password,
        }

    def __str__(self):
        return self.name
