"""Logros de gamificación.

Cambio: Logro.modulo (opcional) permite insignias de un módulo, como
«Maestro de Vocales». Crear la migración con:
    python manage.py makemigrations gamificacion --name agregar_modulo_logro
"""
from django.db import models

from apps.core.models import TipoLogro
from apps.usuarios.models import Usuario


class Logro(models.Model):
    id_logro = models.AutoField(primary_key=True, db_column='id_logro')
    tipo_logro = models.ForeignKey(TipoLogro, on_delete=models.PROTECT, db_column='id_tipo_logro')
    modulo = models.ForeignKey(
        'contenido.Modulo', on_delete=models.SET_NULL, null=True, blank=True,
        db_column='id_modulo', related_name='logros',
    )
    nombre = models.CharField(max_length=100, unique=True, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    meta_valor = models.IntegerField(default=1, db_column='meta_valor')
    icono = models.CharField(max_length=50, blank=True, null=True, db_column='icono')
    xp_bonus = models.IntegerField(default=0, db_column='xp_bonus')

    class Meta:
        db_table = 'logro'
        verbose_name = 'Logro'
        constraints = [
            models.CheckConstraint(condition=models.Q(meta_valor__gt=0), name='ck_logro_meta_valor_positivo'),
            models.CheckConstraint(condition=models.Q(xp_bonus__gte=0), name='ck_logro_xp_bonus_no_negativo'),
        ]

    def __str__(self):
        return self.nombre


class UsuarioLogro(models.Model):
    id_usuario_logro = models.AutoField(primary_key=True, db_column='id_usuario_logro')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    logro = models.ForeignKey(Logro, on_delete=models.PROTECT, db_column='id_logro')
    fecha_obtencion = models.DateTimeField(auto_now_add=True, db_column='fecha_obtencion')

    class Meta:
        db_table = 'usuario_logro'
        verbose_name = 'Logro de Usuario'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'logro'], name='uq_usuario_logro_usuario_logro'),
        ]
