from django import forms
from django.contrib.auth.forms import UserCreationForm
from account.models import CustomUser
from adminpanel.models import Plan, TechSupport

class ResellerForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, label="كلمة المرور")

    class Meta:
        model = CustomUser
        
        fields = [
            "Network_Name",
            "username",
            "Manager_Name",
            "Phone_Number",
            "plan",
        ]

        labels = {
            "Network_Name": "اسم الشبكة",
            "username": "اسم المستخدم",
            "Manager_Name": "اسم المدير",
            "Phone_Number": "رقم الهاتف",
            "plan": "الخطة",
        }
       

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        required_fields = [
            "Network_Name",
            "username",
            "Manager_Name",
            "Phone_Number",
            "plan",
        ]
        
        # If manual password is required for new users
        if not self.instance.pk:
             self.fields['password'].required = True

        for field in required_fields:
            if field in self.fields:
                self.fields[field].required = True
                self.fields[field].error_messages = {
                    "required": "This field cannot be empty"
                }

class PlanForm(forms.ModelForm):
    class Meta:
        model = Plan
        fields = [
            "name",          
            "number_of_servers",
            "number_of_vouchers",
            "price_display",
        ]

        labels = {
            "name": "اسم الخطة",
            "number_of_servers": "عدد الخوادم",
            "number_of_vouchers": "عدد القسائم",
            "price_display": "السعر",
        }


class TechSupportForm(forms.ModelForm):
    class Meta:
        model = TechSupport
        fields = [
            "name",
            "phone",
            "bank_name",
            "bank_account_number",
            "bank_account_holder",
        ]
        labels = {
            "name": "اسم الدعم الفني",
            "phone": "رقم الهاتف",
            "bank_name": "اسم البنك",
            "bank_account_number": "رقم الحساب",
            "bank_account_holder": "اسم صاحب الحساب",
        }

        widgets = {
            "name": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
            "bank_name": forms.TextInput(attrs={"class": "form-input"}),
            "bank_account_number": forms.TextInput(attrs={"class": "form-input"}),
            "bank_account_holder": forms.TextInput(attrs={"class": "form-input"}),
        }

class TechSupportUserForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput,
        label="كلمة المرور"
    )

    class Meta:
        model = CustomUser
        fields = ["username"]

        labels = {
            "username": "اسم المستخدم",
        }
