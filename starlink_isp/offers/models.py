# offers/models.py
from django.db import models
from django.conf import settings


class Offer(models.Model):
   
    reseller = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="offers"
    )

    distributer = models.ForeignKey(
        "distributers.Distributer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="offers"
    )

    name = models.CharField(max_length=100, verbose_name="اسم العرض")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر")

    unlimited_speed = models.BooleanField(default=False, verbose_name="سرعة مفتوحة")
    download_speed = models.PositiveIntegerField(null=True, blank=True, verbose_name="سرعة التحميل")
    upload_speed = models.PositiveIntegerField(null=True, blank=True, verbose_name="سرعة الرفع")

    speed_formula = models.BooleanField(default=False, verbose_name="تفعيل معادلة السرعة")

    DURATION_CHOICES = [
        ("minutes", "دقائق"),
        ("hours", "ساعات"),
        ("days", "أيام"),
        ("months", "شهور"),
    ]

    duration_type = models.CharField(max_length=20, choices=DURATION_CHOICES, verbose_name="نوع المدة")
    duration_value = models.PositiveIntegerField(verbose_name="المدة")

    QUOTA_CHOICES = [
        ("none", "غير محدود"),
        ("MB", "ميجابايت"),
        ("fixed", "محددة (جيجا)"),
    ]

    quota_type = models.CharField(max_length=20, choices=QUOTA_CHOICES, verbose_name="نوع الكوتة")
    quota_amount = models.PositiveIntegerField(null=True, blank=True, verbose_name="كمية الكوتا")

    block_porn_sites = models.BooleanField(default=False, verbose_name="حجب المواقع الإباحية")
    peak_time = models.BooleanField(default=False, verbose_name="وقت الذروة")
    is_available = models.BooleanField(default=True, verbose_name="متاح")

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name