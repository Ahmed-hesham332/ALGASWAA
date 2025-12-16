from django.urls import path
from . import views

app_name = "vouchers"

urlpatterns = [
    path("", views.voucher_list, name="list"),
    path("add/", views.voucher_generate, name="voucher_generate"),
    path("batches/", views.batch_list, name="batch_list"),
]
