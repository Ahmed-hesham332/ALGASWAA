# servers/forms.py
from django import forms
from .models import Server

class ServerForm(forms.ModelForm):
    class Meta:
        model = Server
        fields = [
            "name", 
            "ip_address",

        ]
        labels = {
            "name": "اسم الخادم",
            "ip_address": "عنوان IP",
            
        }
        widgets = {
            "name": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "ip_address": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
        }


