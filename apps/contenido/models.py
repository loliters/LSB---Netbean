from django.db import models
from apps.core.models import Categoria, Dificultad

class Modulo(models.Model):
    id_modulo = models.AutoField(primary_key=True, db_column='id_modulo')
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, db_column='id_categoria', related_name='modulos')
    dificultad = models.ForeignKey(Dificultad, on_delete=models.SET_NULL, null=True, blank=True, db_column='id_dificultad')
    nombre = models.CharField(max_length=100, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    orden = models.PositiveIntegerField(db_column='orden')
    xp_recompensa = models.IntegerField(default=0, db_column='xp_recompensa')
    estado = models.BooleanField(default=True, db_column='estado')

    class Meta:
        db_table = 'modulo'
        ordering = ['categoria', 'orden']
        verbose_name = 'Módulo'
        constraints = [
            models.UniqueConstraint(fields=['categoria', 'orden'], name='uq_modulo_categoria_orden'),
            models.CheckConstraint(condition=models.Q(xp_recompensa__gte=0), name='ck_modulo_xp_no_negativo'),
        ]

    def __str__(self):
        return f'{self.categoria.nombre} – {self.nombre}'


class Leccion(models.Model):
    id_leccion = models.AutoField(primary_key=True, db_column='id_leccion')
    modulo = models.ForeignKey(Modulo, on_delete=models.PROTECT, db_column='id_modulo', related_name='lecciones')
    nombre = models.CharField(max_length=100, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    orden = models.PositiveIntegerField(db_column='orden')
    xp_recompensa = models.IntegerField(default=0, db_column='xp_recompensa')
    estado = models.BooleanField(default=True, db_column='estado')

    class Meta:
        db_table = 'leccion'
        ordering = ['modulo', 'orden']
        verbose_name = 'Lección'
        constraints = [
            models.UniqueConstraint(fields=['modulo', 'orden'], name='uq_leccion_modulo_orden'),
            models.CheckConstraint(condition=models.Q(xp_recompensa__gte=0), name='ck_leccion_xp_no_negativo'),
        ]

    def __str__(self):
        return f'{self.modulo.nombre} - {self.nombre}'


class Sena(models.Model):
    id_sena = models.AutoField(primary_key=True, db_column='id_sena')
    leccion = models.ForeignKey(Leccion, on_delete=models.PROTECT, db_column='id_leccion', related_name='senas')
    tipo_sena = models.ForeignKey('core.TipoSena', on_delete=models.PROTECT, db_column='id_tipo_sena')
    dificultad = models.ForeignKey(Dificultad, on_delete=models.PROTECT, db_column='id_dificultad')
    nombre = models.CharField(max_length=50, db_column='nombre')
    ruta_imagen = models.CharField(max_length=255, db_column='ruta_imagen')
    puntos_minimos = models.IntegerField(default=70, db_column='puntos_minimos')
    estado = models.BooleanField(default=True, db_column='estado')

    class Meta:
        db_table = 'sena'
        verbose_name = 'Seña'
        constraints = [
            models.UniqueConstraint(fields=['leccion', 'nombre'], name='uq_sena_leccion_nombre'),
            models.CheckConstraint(
                condition=models.Q(puntos_minimos__gte=0) & models.Q(puntos_minimos__lte=100), 
                name='ck_sena_puntos_minimos_rango'
            ),
        ]

    def __str__(self):
        return self.nombre