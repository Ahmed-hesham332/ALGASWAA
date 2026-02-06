from django.urls import path
from .active import voucher_usage_view
from .api.install import mikrotik_install, serve_login_html, serve_status_html
from .api.heartbeat import mikrotik_heartbeat

urlpatterns = [
    path("active/voucher/usage", voucher_usage_view, name="voucher_usage_api"),
    path("api/install/<str:token>/login/", serve_login_html, name="install_login_html"),
    path("api/install/<str:token>/status/", serve_status_html, name="install_status_html"),

    path("api/install/<str:token>/<str:version>/", mikrotik_install, name="mikrotik_install"),
    path("api/heartbeat/<str:token>/", mikrotik_heartbeat, name="mikrotik_heartbeat"),
]
