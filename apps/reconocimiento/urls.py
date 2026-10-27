"""Rutas de reconocimiento."""
from django.urls import path

from . import views

app_name = "reconocimiento"

urlpatterns = [
    path("practica/<int:id_sena>/", views.practica, name="practica"),
    path("continuar/", views.continuar, name="continuar"),
    path("predecir/", views.predecir, name="predecir"),
]