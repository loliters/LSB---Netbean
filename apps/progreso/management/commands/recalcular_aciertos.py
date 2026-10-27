"""Completa practica.es_correcta en los intentos guardados antes de la iteración 5.

Uso (una sola vez, después de migrar):
    python manage.py recalcular_aciertos

Regla: un intento antiguo se considera correcto si otorgó XP (xp_ganado > 0).
"""
from django.core.management.base import BaseCommand

from apps.progreso.models import Practica


class Command(BaseCommand):
    help = "Marca como correctos los intentos antiguos que otorgaron XP."

    def handle(self, *args, **options):
        actualizados = Practica.objects.filter(xp_ganado__gt=0, es_correcta=False).update(es_correcta=True)
        self.stdout.write(self.style.SUCCESS(f"Intentos marcados como correctos: {actualizados}"))
