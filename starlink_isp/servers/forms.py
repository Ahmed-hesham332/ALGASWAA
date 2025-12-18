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


