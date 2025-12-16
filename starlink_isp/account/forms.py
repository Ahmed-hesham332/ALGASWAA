# accounts/forms.py
from django import forms
from dashboard.form_utils import set_arabic_error_messages

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label="اسم المستخدم")
    password = forms.CharField(widget=forms.PasswordInput, label="كلمة السر")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_arabic_error_messages(self)
