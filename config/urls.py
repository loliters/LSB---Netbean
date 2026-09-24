from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('usuarios/', include('apps.usuarios.urls')),
    path('contenido/', include('apps.contenido.urls')),
    path(
        '',
        RedirectView.as_view(
            pattern_name='contenido:mapa_modulos',
            permanent=False,
        ),
    ),
]