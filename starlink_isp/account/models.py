# accounts/models.py
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models
from django.utils import timezone
from django.conf import settings


class CustomUser(AbstractUser):
    
    plan = models.ForeignKey("adminpanel.Plan", on_delete=models.SET_NULL, null=True, blank=True)
    tech_support_assigned = models.ForeignKey(
        "adminpanel.TechSupport", 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="resellers"
    )

    groups = models.ManyToManyField(
        Group,
        related_name="customuser_set",
        blank=True,
        help_text="The groups this user belongs to.",
        verbose_name="groups",
    )

    user_permissions = models.ManyToManyField(
        Permission,
        related_name="customuser_set",
        blank=True,
        help_text="Specific permissions for this user.",
        verbose_name="user permissions",
    )

    Network_Name = models.CharField(max_length=100, default=" ")
    Manager_Name = models.CharField(max_length=100, default=" ")
    Phone_Number = models.CharField(max_length=20, default=" ")
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.BooleanField(default=True)
    has_paied = models.BooleanField(default=True)

    def __str__(self):
        return self.username

    @property
    def is_tech_support(self):
        return hasattr(self, "tech_support_profile")

    @property
    def is_distributer(self):
        return hasattr(self, "distributer")

    @property
    def distributer_profile(self):
        if hasattr(self, "distributer"):
            return self.distributer
        return None

    def save(self, *args, **kwargs):
        if not self.pk:
            import random
            while True:
                new_id = random.randint(1000000, 9999999)
                if not CustomUser.objects.filter(pk=new_id).exists():
                    self.pk = new_id
                    break
        super().save(*args, **kwargs)




