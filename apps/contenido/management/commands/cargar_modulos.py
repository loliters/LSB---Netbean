"""Crea los módulos «Vocales» y «Números del 1 al 5» con sus lecciones y señas.

Uso:
    python manage.py cargar_modulos
Idempotente. Las imágenes se vinculan después con: python manage.py vincular_imagenes
"""
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, TipoSena

MODULOS = [
    {"categoria": "Vocales", "modulo": "Vocales", "orden": 1,
     "descripcion": "Las cinco vocales del alfabeto manual: la base para deletrear.",
     "lecciones": [("Vocales abiertas", ["A", "E", "O"]), ("Vocales cerradas", ["I", "U"])]},
    {"categoria": "Números", "modulo": "Números del 1 al 5", "orden": 1,
     "descripcion": "Cuenta con tu mano del 1 al 5. El sistema reconoce cuántos dedos extiendes.",
     "lecciones": [("Números 1 al 3", ["1", "2", "3"]), ("Números 4 y 5", ["4", "5"])]},
]


class Command(BaseCommand):
    help = "Crea los módulos de Vocales y Números con sus lecciones y señas."

    @transaction.atomic
    def handle(self, *args, **options):
        dificultad, _ = Dificultad.objects.get_or_create(
            nivel=1, defaults={"nombre": "Básico", "multiplicador_xp": Decimal("1.00")}
        )
        tipo, _ = TipoSena.objects.get_or_create(nombre="Estática")
        creadas = 0
        for datos in MODULOS:
            categoria, _ = Categoria.objects.get_or_create(nombre=datos["categoria"])
            modulo, _ = Modulo.objects.get_or_create(
                categoria=categoria, orden=datos["orden"],
                defaults={"nombre": datos["modulo"], "descripcion": datos["descripcion"],
                          "dificultad": dificultad, "xp_recompensa": 50},
            )
            for orden, (nombre_leccion, senas) in enumerate(datos["lecciones"], start=1):
                leccion, _ = Leccion.objects.get_or_create(
                    modulo=modulo, orden=orden, defaults={"nombre": nombre_leccion, "xp_recompensa": 20}
                )
                for nombre in senas:
                    _, nueva = Sena.objects.get_or_create(
                        leccion=leccion, nombre=nombre,
                        defaults={"tipo_sena": tipo, "dificultad": dificultad,
                                  "ruta_imagen": f"senas/{nombre.lower()}.png",
                                  "puntos_minimos": 70 if nombre.isdigit() else 80},
                    )
                    creadas += int(nueva)
        self.stdout.write(self.style.SUCCESS(f"Listo: {creadas} señas nuevas en Vocales y Números."))
