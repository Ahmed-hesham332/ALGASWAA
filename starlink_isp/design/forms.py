from django import forms
from .models import Design

class DesignForm(forms.ModelForm):
    class Meta:
        model = Design
        fields = [
            "name",
            "background_image",
            "serial_x",
            "serial_y",
            "serial_font_size",
            "serial_color",
        ]
        widgets = {
            "serial_x": forms.HiddenInput(),
            "serial_y": forms.HiddenInput(),
        }
