from django.db import models
from django.conf import settings

class Distributer(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="distributer"
    )
    reseller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="distributers_created"
    )
    
    # Servers
    servers = models.ManyToManyField("servers.Server", blank=True, related_name="distributers")
    
    # Status
    status = models.BooleanField(default=True)

    # Permissions - Offers
    can_view_offers = models.BooleanField(default=False)
    can_add_offer = models.BooleanField(default=False)
    can_edit_offer = models.BooleanField(default=False)
    can_delete_offer = models.BooleanField(default=False)

    # Permissions - Designs
    can_view_designs = models.BooleanField(default=False)
    can_add_design = models.BooleanField(default=False)
    can_delete_design = models.BooleanField(default=False)

    # Permissions - Vouchers
    can_view_vouchers = models.BooleanField(default=False)
    can_add_voucher = models.BooleanField(default=False)
    
    def __str__(self):
        return self.user.username
