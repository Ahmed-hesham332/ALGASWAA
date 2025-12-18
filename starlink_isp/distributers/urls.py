from django.urls import path
from .views import distributer_list, distributer_add, distributer_edit, distributer_delete

app_name = "distributers"

urlpatterns = [
    path("", distributer_list, name="distributer_list"),
    path("add/", distributer_add, name="distributer_add"),
    path("<int:pk>/edit/", distributer_edit, name="distributer_edit"),
    path("<int:pk>/delete/", distributer_delete, name="distributer_delete"),
]
