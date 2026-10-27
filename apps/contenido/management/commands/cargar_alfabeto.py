"""Carga datos semilla mínimos para probar la práctica con IA.

Uso:
    python manage.py cargar_alfabeto
Idempotente: se puede ejecutar varias veces sin duplicar registros.
"""
import string
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, Rol, TipoSena


def _leer_letras() -> list[str]:
    ruta = Path(settings.RUTA_ETIQUETAS)
    if ruta.exists():
        lineas = ruta.read_text(encoding="utf-8").splitlines()
        # Solo letras: las clases "_" (espacio) y "!" no son señas de una lección.
        return [linea.strip().upper() for linea in lineas if linea.strip().isalpha()]
    return list(string.ascii_uppercase)


class Command(BaseCommand):
    help = "Crea roles, catálogos y el módulo Alfabeto con una seña por etiqueta del modelo."

    @transaction.atomic
    def handle(self, *args, **options):
        for nombre in ("Estudiante", "Profesor", "Administrador"):
            Rol.objects.get_or_create(nombre_rol=nombre)
        dificultad, _ = Dificultad.objects.get_or_create(
            nivel=1, defaults={"nombre": "Básico", "multiplicador_xp": Decimal("1.00")}
        )
        tipo, _ = TipoSena.objects.get_or_create(nombre="Estática")
        categoria, _ = Categoria.objects.get_or_create(nombre="Alfabeto")
        modulo, _ = Modulo.objects.get_or_create(
            categoria=categoria, orden=1, defaults={"nombre": "Alfabeto", "dificultad": dificultad}
        )
        leccion, _ = Leccion.objects.get_or_create(modulo=modulo, orden=1, defaults={"nombre": "Letras"})
        creadas = 0
        for letra in _leer_letras():
            _, nueva = Sena.objects.get_or_create(
                leccion=leccion,
                nombre=letra,
                defaults={
                    "tipo_sena": tipo,
                    "dificultad": dificultad,
                    "ruta_imagen": f"senas/{letra.lower()}.png",
                    "puntos_minimos": 80,
                },
            )
            creadas += int(nueva)
        self.stdout.write(self.style.SUCCESS(f"Listo: {creadas} señas nuevas en '{modulo.nombre}'."))