"""Receptores de gamificación. Delegan la lógica en services.py."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.progreso.models import Practica

from . import services


@receiver(post_save, sender=Practica, dispatch_uid="gamificacion_aplicar_practica")
def aplicar_practica(sender, instance: Practica, created: bool, raw: bool = False, **kwargs):
    """Aplica XP y racha solo al crear la práctica (idempotente ante updates)."""
    if created and not raw:
        services.aplicar_recompensa(instance)
