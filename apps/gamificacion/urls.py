"""Rutas de gamificación."""
from django.urls import path

from . import views

app_name = "gamificacion"

urlpatterns = [
    path("evaluar/", views.evaluar, name="evaluar"),
    path("progreso/", views.progreso, name="progreso"),
]
