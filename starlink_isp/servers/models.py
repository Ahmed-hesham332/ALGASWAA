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
        # Always save first
        super().save(*args, **kwargs)
        
        if not self.hostname:
            self.hostname = f"{self.owner.id}_{self.id}"
            # Update hostname without triggering recursion issues if we use update_fields
            super().save(update_fields=['hostname'])


    @property
    def install_token(self):
        return f"{self.owner.id}_{self.id}"

    def __str__(self):
        return self.name
