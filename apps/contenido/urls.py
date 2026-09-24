from django.urls import path

from . import views

app_name = 'contenido'

urlpatterns = [
    path('modulos/', views.mapa_modulos, name='mapa_modulos'),
]