from django.urls import path
from . import views

app_name = "online"

urlpatterns = [
    path("", views.online_list, name="list"),
]

