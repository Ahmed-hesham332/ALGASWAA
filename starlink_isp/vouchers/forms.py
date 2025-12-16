from django import forms
from dashboard.form_utils import set_arabic_error_messages


class VoucherGenerationForm(forms.Form):

    server = forms.ModelChoiceField(queryset=None, label="السيرفر")
    offer = forms.ModelChoiceField(queryset=None, label="العرض")

    name = forms.CharField(max_length=100, label="اسم المجموعة")
    quantity = forms.IntegerField(label="عدد الكروت")

    serial_length = forms.IntegerField(min_value=4, max_value=20, initial=8)
    serial_type = forms.ChoiceField(choices=[("numeric","أرقام"), ("alphanumeric","أرقام وحروف")])
    prefix = forms.CharField(max_length=10, required=False)

    def __init__(self, *args, **kwargs):
        reseller = kwargs.pop("reseller")
        super().__init__(*args, **kwargs)
        self.fields["server"].queryset = reseller.servers.all()
        self.fields["offer"].queryset = reseller.offers.all()
