"""Rutas de la aplicación de usuarios."""
from django.urls import path

from . import gestion, views

app_name = "usuarios"

urlpatterns = [
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("registro/", views.registro_view, name="registro"),
    path("recuperar/", views.recuperar_password_view, name="recuperar_password"),
    path("restablecer/<str:token>/", views.restablecer_password_view, name="restablecer_password"),
    path("panel/", views.panel, name="panel"),
    path("panel/estudiante/", views.panel_estudiante, name="panel_estudiante"),
    path("panel/profesor/", views.panel_profesor, name="panel_profesor"),
    path("panel/admin/", views.panel_admin, name="panel_admin"),
    path("gestion/usuarios/", gestion.UsuarioListView.as_view(), name="gestion_usuarios"),
    path("gestion/usuarios/nuevo/", gestion.UsuarioCrearView.as_view(), name="gestion_usuario_nuevo"),
    path(
        "gestion/usuarios/<int:id_usuario>/editar/",
        gestion.UsuarioEditarView.as_view(),
        name="gestion_usuario_editar",
    ),
    path(
        "gestion/usuarios/<int:id_usuario>/estado/",
        gestion.UsuarioCambiarEstadoView.as_view(),
        name="gestion_usuario_estado",
    ),
]