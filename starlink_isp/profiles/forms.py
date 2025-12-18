from django import forms
from account.models import CustomUser

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "first_name",
            "Network_Name",
            "Manager_Name",
            "Phone_Number",
        ]
        labels = {
            "first_name": "الاسم",
            "Network_Name": "اسم الشبكة",
            "Manager_Name": "اسم المدير",
            "Phone_Number": "رقم الجوال",
        }

        widgets = {
            "first_name": forms.TextInput(attrs={"class": "form-input"}),
            "Network_Name": forms.TextInput(attrs={"class": "form-input"}),
            "Manager_Name": forms.TextInput(attrs={"class": "form-input"}),
            "Phone_Number": forms.TextInput(attrs={"class": "form-input"}),
        }


class PasswordChangeCustomForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
        label="كلمة المرور القديمة"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
        label="كلمة المرور الجديدة"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
        label="تأكيد كلمة المرور"
    )

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        if new != confirm:
            raise forms.ValidationError("كلمتا المرور غير متطابقتين")

        return cleaned
