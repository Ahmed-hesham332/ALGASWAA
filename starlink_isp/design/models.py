from django.db import models
from django.conf import settings
from servers.models import Server
from .validate import validate_image, validate_image_size   

class Design(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="designs"
    )

    name = models.CharField(max_length=100)
    background_image = models.ImageField(
        upload_to="designs/", 
        validators=[validate_image, validate_image_size], default="media/designs/backgrounds/card_background.jpg"
    )

    serial_x = models.IntegerField(default=70)
    serial_y = models.IntegerField(default=100)
    serial_font_size = models.IntegerField(default=18)
    serial_color = models.CharField(max_length=7, default="#000000")

    preview_image = models.ImageField(
        upload_to="media/previews/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
