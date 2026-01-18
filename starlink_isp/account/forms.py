# accounts/forms.py
from django import forms
from dashboard.form_utils import set_arabic_error_messages

class LoginForm(forms.Form):
    username = forms.CharField(max_length=100, label="اسم المستخدم")
    password = forms.CharField(widget=forms.PasswordInput, label="كلمة السر")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_arabic_error_messages(self)
        
        # Tailwind classes for form inputs
        css_classes = "w-full bg-muted/50 border border-border rounded-xl px-4 py-3 text-foreground focus:outline-none focus:ring-2 focus:ring-primary/50 transition-all placeholder:text-muted-foreground/50"
        
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': css_classes})


