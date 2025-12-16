# offers/urls.py
from django.urls import path
from . import views

app_name = "offers"

urlpatterns = [
    path("", views.offer_list, name="offer_list"),
    path("add/", views.offer_add, name="offer_add"),
    path("<int:offer_id>/edit/", views.offer_edit, name="offer_edit"),
    path("<int:offer_id>/delete/", views.offer_delete, name="offer_delete"),
]
