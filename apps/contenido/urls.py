"""Rutas de contenido."""
from django.urls import path

from . import views

app_name = "contenido"

urlpatterns = [
    path("modulos/", views.mapa_modulos, name="mapa_modulos"),
    path("modulos/<int:id_modulo>/", views.detalle_modulo, name="detalle_modulo"),
]
