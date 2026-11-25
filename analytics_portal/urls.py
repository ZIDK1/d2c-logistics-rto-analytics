from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="dashboard_home"),
    path("api/summary/", views.api_summary, name="api_summary"),
    path("api/orders/", views.api_orders, name="api_orders"),
    path("api/export.csv", views.api_export_csv, name="api_export_csv"),
]
