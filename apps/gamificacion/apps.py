from django.apps import AppConfig


class GamificacionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.gamificacion"
    verbose_name = "Gamificación"

    def ready(self) -> None:
        from . import signals  # noqa: F401  registra los receptores
