from django import forms
from dashboard.form_utils import set_arabic_error_messages
from account.models import CustomUser
from .models import Distributer
from servers.models import Server

class DistributerUserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=False, label="كلمة السر")
    
    class Meta:
        model = CustomUser
        fields = ["username", "first_name", "password"]
        labels = {
            "username": "اسم المستخدم",
            "first_name": "الاسم",
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        set_arabic_error_messages(self)
        if self.instance.pk:
            self.fields["password"].help_text = "اترك الحقل فارغاً إذا كنت لا تريد تغيير كلمة السر"

class DistributerPermissionsForm(forms.ModelForm):
    servers = forms.ModelMultipleChoiceField(
        queryset=Server.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
        label="الخوادم المتاحة"
    )

    class Meta:
        model = Distributer
        fields = [
            "servers", "status", 
            "can_view_offers", "can_add_offer", "can_edit_offer", "can_delete_offer",
            "can_view_designs", "can_add_design", "can_delete_design",
            "can_view_vouchers", "can_add_voucher"
        ]
        labels = {
            "status": "مفعل",
            "can_view_offers": "عرض العروض",
            "can_add_offer": "إضافة عرض",
            "can_edit_offer": "تعديل عرض",
            "can_delete_offer": "حذف عرض",
            "can_view_designs": "عرض التصاميم",
            "can_add_design": "إضافة تصميم",
            "can_delete_design": "حذف تصميم",
            "can_view_vouchers": "عرض الكروت",
            "can_add_voucher": "إضافة كرت",
        }

    def __init__(self, reseller=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter servers to only those owned by the reseller
        if reseller:
            self.fields["servers"].queryset = Server.objects.filter(owner=reseller)
        set_arabic_error_messages(self)
