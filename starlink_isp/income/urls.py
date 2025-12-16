from django.urls import path
from .views import income_report

urlpatterns = [
    path("", income_report, name="income_report"),
]
