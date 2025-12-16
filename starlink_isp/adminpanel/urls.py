from django.urls import path
from . import views

app_name = "adminpanel"

urlpatterns = [
    # tech support: Reseller Management
    path("resellers/", views.reseller_list, name="reseller_list"),
    path("resellers/add/", views.reseller_add, name="reseller_add"),
    path("resellers/<int:user_id>/edit/", views.reseller_edit, name="reseller_edit"),
    path("resellers/<int:user_id>/delete/", views.reseller_delete, name="reseller_delete"),
    path("servers/", views.server_list, name="server_list"),
    path("servers/<int:server_id>/delete/", views.server_delete, name="server_delete"),

    path("profile/", views.profile, name="profile"),

    path("resellers/delete-unpaid/", views.delete_unpaid_resellers, name="delete_unpaid_resellers"),

    path(
        "reseller/toggle-status/<int:reseller_id>/",
        views.reseller_toggle_status,
        name="reseller_toggle_status"
    ),
    path(
        "reseller/toggle-paied/<int:reseller_id>/",
        views.reseller_toggle_paied,
        name="reseller_toggle_paied"
    ),
    # SuperAdmin: Tech Support Management
    path("tech-supports/", views.tech_support_list, name="tech_support_list"),
    path("tech-supports/add/", views.tech_support_add, name="tech_support_add"),
    path("tech-supports/<int:tech_id>/edit/", views.tech_support_edit, name="tech_support_edit"),
    path("tech-supports/<int:tech_id>/delete/", views.tech_support_delete, name="tech_support_delete"),
    path("plans/", views.plan_list, name="plan_list"),
    path("plans/add/", views.plan_add, name="plan_add"),
    path("plans/<int:plan_id>/edit/", views.plan_edit, name="plan_edit"),
    path("plans/<int:plan_id>/delete/", views.plan_delete, name="plan_delete"),

]
