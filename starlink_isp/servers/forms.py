# servers/forms.py
from django import forms
from .models import Server

class ServerForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = [
            "name", 
            "ip_address",
            "serial_number",
            "api_password",
        ]
        labels = {
            "name": "اسم الخادم",
            "ip_address": "عنوان IP",
            "serial_number": "رقم التسلسلي",
            "api_password": "كلمة المرور",
        }
        widgets = {
            "api_password": forms.PasswordInput(),
        }

