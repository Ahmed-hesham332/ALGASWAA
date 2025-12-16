from django.urls import path
from .api import voucher_usage_view

urlpatterns = [
    path("api/usage", voucher_usage_view, name="voucher_usage_api"),
]
