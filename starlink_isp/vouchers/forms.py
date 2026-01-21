from django import forms
from dashboard.form_utils import set_arabic_error_messages


class VoucherGenerationForm(forms.Form):

    server = forms.ModelChoiceField(queryset=None, label="السيرفر", widget=forms.Select(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))
    offer = forms.ModelChoiceField(queryset=None, label="العرض", widget=forms.Select(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))

    name = forms.CharField(max_length=100, label="اسم المجموعة", widget=forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))
    quantity = forms.IntegerField(label="عدد الكروت", widget=forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))

    serial_length = forms.IntegerField(min_value=4, max_value=20, initial=8, widget=forms.NumberInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))
    serial_type = forms.ChoiceField(choices=[("numeric","أرقام"), ("alphanumeric","أرقام وحروف")], widget=forms.Select(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))
    prefix = forms.CharField(max_length=10, required=False, widget=forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}))

    def __init__(self, *args, **kwargs):
        reseller = kwargs.pop("reseller")
        super().__init__(*args, **kwargs)
        self.fields["server"].queryset = reseller.servers.all()
        self.fields["offer"].queryset = reseller.offers.all()
