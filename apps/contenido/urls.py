"""Rutas de contenido: catálogo (HU-03, HU-04) y gestión (HU-08)."""
from django.urls import path

from . import gestion, views

app_name = "contenido"

urlpatterns = [
    path("modulos/", views.mapa_modulos, name="mapa_modulos"),
    path("modulos/<int:id_modulo>/", views.detalle_modulo, name="detalle_modulo"),
    # Gestión (administrador y profesor)
    path("gestion/", gestion.ModuloListView.as_view(), name="gestion_modulos"),
    path("gestion/modulos/nuevo/", gestion.ModuloCrearView.as_view(), name="gestion_modulo_nuevo"),
    path("gestion/modulos/<int:id_modulo>/editar/", gestion.ModuloEditarView.as_view(), name="gestion_modulo_editar"),
    path("gestion/modulos/<int:id_modulo>/lecciones/", gestion.LeccionListView.as_view(), name="gestion_lecciones"),
    path(
        "gestion/modulos/<int:id_modulo>/lecciones/nueva/",
        gestion.LeccionCrearView.as_view(),
        name="gestion_leccion_nueva",
    ),
    path("gestion/lecciones/<int:id_leccion>/editar/", gestion.LeccionEditarView.as_view(), name="gestion_leccion_editar"),
    path("gestion/lecciones/<int:id_leccion>/senas/", gestion.SenaListView.as_view(), name="gestion_senas"),
    path("gestion/lecciones/<int:id_leccion>/senas/nueva/", gestion.SenaCrearView.as_view(), name="gestion_sena_nueva"),
    path("gestion/senas/<int:id_sena>/editar/", gestion.SenaEditarView.as_view(), name="gestion_sena_editar"),
    path("gestion/<str:tipo>/<int:pk>/estado/", gestion.CambiarEstadoView.as_view(), name="gestion_estado"),
]
