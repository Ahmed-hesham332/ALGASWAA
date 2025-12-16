from django.urls import path
from . import views

app_name = "design"

urlpatterns = [
    path('', views.design_list, name='list'),
    path('add/', views.design_add, name='design_add'),
    path('delete/<int:design_id>/', views.design_delete, name='delete'),
    path("download/<int:design_id>/", views.download_design_pdf, name="download_pdf"),
]
