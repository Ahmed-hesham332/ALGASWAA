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
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    id = models.AutoField(primary_key=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    hostname = models.CharField(max_length=64, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.id:
            super().save(*args, **kwargs)
        
        if not self.hostname:
            self.hostname = f"{self.owner.id}_{self.id}"
            super().save(update_fields=['hostname'])


    @property
    def install_token(self):
        return f"{self.owner.id}_{self.id}"

    def __str__(self):
        return self.name

# Signal to delete from RADIUS when Server is deleted
from django.db.models.signals import post_delete
from django.dispatch import receiver
from radius_integration.services import radius_delete_client

@receiver(post_delete, sender=Server)
def delete_server_from_radius(sender, instance, **kwargs):
    if instance.hostname:
        radius_delete_client(instance.hostname)
