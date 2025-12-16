# servers/urls.py
from django.urls import path
from . import views

app_name = "servers"

urlpatterns = [
    path("", views.server_list, name="list"),
    path("add/", views.server_add, name="add"),
    path("<int:server_id>/edit/", views.server_edit, name="edit"),
    path("<int:server_id>/delete/", views.server_delete, name="delete"),
    path("<int:server_id>/download/", views.server_download, name="download"),

]

