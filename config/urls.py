"""Rutas raíz del proyecto Net Bean."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.core.views import inicio
from apps.usuarios import views as usuarios_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", inicio, name="inicio"),
    path("usuarios/", include("apps.usuarios.urls")),
    path("contenido/", include("apps.contenido.urls")),
    path("reconocimiento/", include("apps.reconocimiento.urls")),
    path("gamificacion/", include("apps.gamificacion.urls")),
    path(
        "api/recuperar-password",
        usuarios_views.api_recuperar_password,
        name="api_recuperar_password",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
