"""Carga tipos de logro, logros y niveles iniciales (HU-11).

Uso (después de cargar_modulos, para enlazar las insignias de módulo):
    python manage.py cargar_logros
Idempotente: no duplica registros si se ejecuta varias veces.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contenido.models import Modulo
from apps.core.models import Nivel, TipoLogro
from apps.gamificacion.models import Logro

TIPOS = {
    "practicas": ("Constancia", "Cantidad de prácticas registradas"),
    "racha": ("Racha", "Días seguidos practicando con aciertos"),
    "dominadas": ("Dominio", "Señas aprobadas con el mínimo requerido"),
    "nivel": ("Nivel", "Nivel alcanzado según el XP total"),
}
LOGROS = [
    ("Primer paso", "Registra tu primera práctica.", "practicas", 1, "flag-fill", 10),
    ("Practicante", "Registra 25 prácticas.", "practicas", 25, "lightning-charge-fill", 30),
    ("Imparable", "Registra 100 prácticas.", "practicas", 100, "rocket-takeoff-fill", 80),
    ("Racha de 3 días", "Acierta al menos una seña 3 días seguidos.", "racha", 3, "fire", 30),
    ("Racha de 7 días", "Acierta al menos una seña 7 días seguidos.", "racha", 7, "calendar-check-fill", 70),
    ("Primeras 5 señas", "Domina 5 señas.", "dominadas", 5, "hand-thumbs-up-fill", 40),
    ("Maestro del alfabeto", "Domina 27 señas.", "dominadas", 27, "alphabet-uppercase", 150),
    ("Nivel 3", "Alcanza el nivel 3.", "nivel", 3, "star-fill", 50),
    ("Nivel 5", "Alcanza el nivel 5.", "nivel", 5, "trophy-fill", 100),
    ("Racha de Fuego", "Practica con aciertos 5 días seguidos.", "racha", 5, "fire", 50),
    ("Diez prácticas", "Registra 10 prácticas.", "practicas", 10, "emoji-smile-fill", 20),
]
# (nombre, descripción, módulo, meta, icono, xp): dominar todas las señas de un módulo
LOGROS_DE_MODULO = [
    ("Maestro de Vocales", "Domina las 5 vocales: A, E, I, O y U.", "Vocales", 5, "mortarboard-fill", 60),
    ("Experto en Números", "Domina los números del 1 al 5.", "Números del 1 al 5", 5, "123", 60),
]
NIVELES = [(1, "Principiante", 0), (2, "Aprendiz", 100), (3, "Intermedio", 300), (4, "Avanzado", 600), (5, "Experto", 1000)]


class Command(BaseCommand):
    help = "Crea los tipos de logro, los logros y los niveles iniciales."

    @transaction.atomic
    def handle(self, *args, **options):
        if not Nivel.objects.exists():
            for numero, nombre, xp in NIVELES:
                Nivel.objects.create(numero_nivel=numero, nombre_nivel=nombre, xp_requerido=xp)
        tipos = {}
        for metrica, (nombre, descripcion) in TIPOS.items():
            tipos[metrica], _ = TipoLogro.objects.get_or_create(
                metrica=metrica, defaults={"nombre": nombre, "descripcion": descripcion}
            )
        # Renombra la insignia antigua (conserva a quienes ya la ganaron)
        Logro.objects.filter(nombre="Amigo de Ugg").update(
            nombre="Diez prácticas", descripcion="Registra 10 prácticas.", icono="emoji-smile-fill")
        creados = 0
        for nombre, descripcion, metrica, meta, icono, xp in LOGROS:
            _, nuevo = Logro.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "tipo_logro": tipos[metrica],
                          "meta_valor": meta, "icono": icono, "xp_bonus": xp},
            )
            creados += int(nuevo)
        for nombre, descripcion, nombre_modulo, meta, icono, xp in LOGROS_DE_MODULO:
            modulo = Modulo.objects.filter(nombre=nombre_modulo).first()
            if modulo is None:
                self.stdout.write(self.style.WARNING(
                    f"Se omitió «{nombre}»: falta el módulo «{nombre_modulo}» (ejecuta cargar_modulos)."))
                continue
            logro, nuevo = Logro.objects.get_or_create(
                nombre=nombre,
                defaults={"descripcion": descripcion, "tipo_logro": tipos["dominadas"], "modulo": modulo,
                          "meta_valor": meta, "icono": icono, "xp_bonus": xp},
            )
            if not nuevo and logro.modulo_id != modulo.pk:
                logro.modulo = modulo
                logro.save(update_fields=["modulo"])
            creados += int(nuevo)
        self.stdout.write(self.style.SUCCESS(f"Listo: {creados} logros nuevos; {Nivel.objects.count()} niveles."))
