"""Gestión de módulos, lecciones y señas en el admin de Django (HU-08)."""
from django.contrib import admin

from .models import Leccion, Modulo, Sena


class LeccionInline(admin.TabularInline):
    model = Leccion
    extra = 0
    fields = ("orden", "nombre", "xp_recompensa", "estado")


class SenaInline(admin.TabularInline):
    model = Sena
    extra = 0
    fields = ("nombre", "tipo_sena", "dificultad", "ruta_imagen", "puntos_minimos", "estado")


@admin.register(Modulo)
class ModuloAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "orden", "dificultad", "estado")
    list_filter = ("categoria", "dificultad", "estado")
    search_fields = ("nombre",)
    inlines = (LeccionInline,)


@admin.register(Leccion)
class LeccionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "modulo", "orden", "estado")
    list_filter = ("modulo", "estado")
    inlines = (SenaInline,)


@admin.register(Sena)
class SenaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "leccion", "tipo_sena", "dificultad", "puntos_minimos", "estado")
    list_filter = ("leccion__modulo", "dificultad", "estado")
    list_editable = ("puntos_minimos", "estado")
    search_fields = ("nombre",)