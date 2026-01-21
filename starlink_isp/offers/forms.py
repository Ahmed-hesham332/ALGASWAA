# offers/forms.py
from django import forms
from .models import Offer
from dashboard.form_utils import set_arabic_error_messages


class OfferForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_arabic_error_messages(self)

    class Meta:
        model = Offer
        fields = [
            "name",
            "price",
            "unlimited_speed",
            "download_speed",
            "upload_speed",
            # "speed_formula",
            "duration_type",
            "duration_value",
            "quota_type",
            "quota_amount",
            "block_porn_sites",
            # "peak_time",
            # "is_available",
        ]

        widgets = {
            "name": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "price": forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm", "step": "0.01"}),
            "download_speed": forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm", "placeholder": "kbps"}),
            "upload_speed": forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm", "placeholder": "kbps"}),
            "duration_value": forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm", "min": 1}),
            "quota_amount": forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm", "placeholder": "GB"}),
            "duration_type": forms.Select(choices=Offer.DURATION_CHOICES, attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "quota_type": forms.Select(choices=Offer.QUOTA_CHOICES, attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
        }

        labels = {
            "name": "اسم العرض",
            "price": "السعر",
            "unlimited_speed": "سرعة مفتوحة",
            "download_speed": "سرعة التحميل (kbps)",
            "upload_speed": "سرعة الرفع (kbps)",
            # "speed_formula": "تفعيل معادلة السرعة",
            "duration_type": "نوع المدة",
            "duration_value": "المدة",
            "quota_type": "نوع الكوتة",
            "quota_amount": "كمية الكوتا",
            "block_porn_sites": "حجب المواقع الإباحية",
            # "peak_time": "وقت الذروة",
            # "is_available": "متاح",
        }
