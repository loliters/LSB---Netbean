"""Vincula cada seña con su imagen de referencia en media/senas/.

Uso:
    python manage.py vincular_imagenes

Busca un archivo con el nombre de la seña en minúscula (a.jpg, b.png, ñ.webp...).
Si no lo encuentra, deja ruta_imagen vacía para que no se muestre una imagen rota.
"""
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.contenido.models import Sena

EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp")
CARPETA = "senas"


class Command(BaseCommand):
    help = "Asigna a cada seña su imagen de media/senas/ según su nombre."

    def handle(self, *args, **options):
        carpeta = Path(settings.MEDIA_ROOT) / CARPETA
        carpeta.mkdir(parents=True, exist_ok=True)
        encontradas, faltantes = 0, []
        for sena in Sena.objects.all():
            archivo = next(
                (carpeta / f"{sena.nombre.lower()}{ext}" for ext in EXTENSIONES
                 if (carpeta / f"{sena.nombre.lower()}{ext}").exists()),
                None,
            )
            sena.ruta_imagen = f"{CARPETA}/{archivo.name}" if archivo else ""
            sena.save(update_fields=["ruta_imagen"])
            if archivo:
                encontradas += 1
            else:
                faltantes.append(sena.nombre)
        self.stdout.write(self.style.SUCCESS(f"Imágenes vinculadas: {encontradas}"))
        if faltantes:
            self.stdout.write(self.style.WARNING(f"Sin imagen: {', '.join(faltantes)}"))
        self.stdout.write(f"Carpeta: {carpeta}")