from django.urls import path
from .active import voucher_usage_view
from .api.install import mikrotik_install

urlpatterns = [
    path("api/usage", voucher_usage_view, name="voucher_usage_api"),
    path("api/install/<str:token>/<str:version>/", mikrotik_install, name="mikrotik_install"),
]
