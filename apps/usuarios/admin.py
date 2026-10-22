"""Registro en el admin de Django (uso avanzado; la gestión diaria está en /usuarios/gestion/)."""
from django.contrib import admin

from .models import EstadisticasUsuario, TokenRecuperacion, Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("correo", "nombre", "apellido", "rol", "estado", "fecha_registro")
    list_filter = ("rol", "estado")
    search_fields = ("correo", "nombre", "apellido")
    fields = ("nombre", "apellido", "correo", "rol", "estado", "es_staff", "es_superuser", "is_superuser")
    actions = ("desactivar", "reactivar")

    @admin.action(description="Desactivar cuentas seleccionadas")
    def desactivar(self, request, queryset):
        queryset.exclude(pk=request.user.pk).update(estado=False)

    @admin.action(description="Reactivar cuentas seleccionadas")
    def reactivar(self, request, queryset):
        queryset.update(estado=True)


@admin.register(EstadisticasUsuario)
class EstadisticasUsuarioAdmin(admin.ModelAdmin):
    list_display = ("usuario", "xp_total", "racha_dias", "total_practicas", "ultima_practica")
    search_fields = ("usuario__correo",)


@admin.register(TokenRecuperacion)
class TokenRecuperacionAdmin(admin.ModelAdmin):
    list_display = ("usuario", "fecha_creacion", "fecha_expiracion", "usado")
    readonly_fields = ("token_hash", "fecha_creacion")