from django.urls import path
from . import views

app_name = "landing"

urlpatterns = [
    path("", views.landing_index, name="landing_index"),
]
