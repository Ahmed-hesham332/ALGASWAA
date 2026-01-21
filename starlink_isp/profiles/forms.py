from django import forms
from account.models import CustomUser

class ProfileForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = [
            "Network_Name",
            "Manager_Name",
            "Phone_Number",
        ]
        labels = {
            "Network_Name": "اسم الشبكة",
            "Manager_Name": "اسم المدير",
            "Phone_Number": "رقم الجوال",
        }

        widgets = {
            "Network_Name": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "Manager_Name": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
            "Phone_Number": forms.TextInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
        }


class PasswordChangeCustomForm(forms.Form):
    old_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
        label="كلمة المرور القديمة"
    )
    new_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
        label="كلمة المرور الجديدة"
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "cyber-input w-full rounded-xl px-4 py-3 text-sm"}),
        label="تأكيد كلمة المرور"
    )

    def clean(self):
        cleaned = super().clean()
        new = cleaned.get("new_password")
        confirm = cleaned.get("confirm_password")

        if new != confirm:
            raise forms.ValidationError("كلمتا المرور غير متطابقتين")

        return cleaned
