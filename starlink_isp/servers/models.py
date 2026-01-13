# servers/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta

class Server(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="servers"
    )

    name = models.CharField(max_length=200)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    id = models.AutoField(primary_key=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    hostname = models.CharField(max_length=64, unique=True, blank=True, null=True)
    tunnel_ip = models.GenericIPAddressField(unique=True, null=True, blank=True)
    tunnel_password = models.CharField(max_length=64, blank=True)
    last_heartbeat = models.DateTimeField(null=True, blank=True, default='1970-01-01 00:00:00')

    def save(self, *args, **kwargs):
        # Always save first
        super().save(*args, **kwargs)
        
        if not self.hostname:
            self.hostname = f"{self.owner.id}_{self.id}"
            self.tunnel_password = self.hostname  # simplest for now
            super().save(update_fields=["hostname", "tunnel_password"])


    @property
    def install_token(self):
        return f"{self.owner.id}_{self.id}"

    @property
    def is_online(self):
        if not self.last_heartbeat:
            return False
        return timezone.now() - self.last_heartbeat < timedelta(minutes=2)

    def __str__(self):
        return self.name
