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
            "name": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "background_image": forms.FileInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-accent/10 file:text-accent hover:file:bg-accent/20"}),
            "serial_x": forms.HiddenInput(),
            "serial_y": forms.HiddenInput(), 
            "serial_font_size": forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "serial_color": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm", "type": "color", "style": "height: 50px; padding: 2px;"}),
        }
