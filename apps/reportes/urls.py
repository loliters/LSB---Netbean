"""Rutas de reportes."""
from django.urls import path

from . import views

app_name = "reportes"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("excel/", views.exportar_excel, name="exportar_excel"),
    path("pdf/", views.exportar_pdf, name="exportar_pdf"),
]
