from django.db import models
from apps.usuarios.models import Usuario
from apps.contenido.models import Sena, Leccion
from apps.core.models import EstadoProgreso

class ProgresoSena(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    sena = models.ForeignKey(Sena, on_delete=models.CASCADE, db_column='id_sena')
    mejor_puntaje = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_column='mejor_puntaje')
    intentos = models.IntegerField(default=0, db_column='intentos')
    dominada = models.BooleanField(default=False, db_column='dominada')

    class Meta:
        db_table = 'progreso_sena'
        verbose_name = 'Progreso de Seña'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'sena'], name='pk_progreso_sena_usuario_sena'),
            models.CheckConstraint(
                condition=models.Q(mejor_puntaje__gte=0) & models.Q(mejor_puntaje__lte=100), 
                name='ck_progreso_sena_puntaje_rango'
            ),
            models.CheckConstraint(condition=models.Q(intentos__gte=0), name='ck_progreso_sena_intentos_no_negativo'),
        ]


class ProgresoLeccion(models.Model):
    id_progreso = models.AutoField(primary_key=True, db_column='id_progreso')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    leccion = models.ForeignKey(Leccion, on_delete=models.CASCADE, db_column='id_leccion')
    estado = models.ForeignKey(EstadoProgreso, on_delete=models.PROTECT, db_column='id_estado')
    fecha_inicio = models.DateTimeField(auto_now_add=True, db_column='fecha_inicio')
    fecha_completado = models.DateTimeField(null=True, blank=True, db_column='fecha_completado')

    class Meta:
        db_table = 'progreso_leccion'
        verbose_name = 'Progreso de Lección'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'leccion'], name='uq_progreso_leccion_usuario_leccion'),
        ]


class Practica(models.Model):
    id_practica = models.BigAutoField(primary_key=True, db_column='id_practica')
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, db_column='id_usuario')
    sena = models.ForeignKey(Sena, on_delete=models.PROTECT, db_column='id_sena')
    numero_intento = models.IntegerField(db_column='numero_intento')
    fecha_practica = models.DateTimeField(auto_now_add=True, db_column='fecha_practica')
    puntaje_obtenido = models.DecimalField(max_digits=5, decimal_places=2, db_column='puntaje_obtenido')
    xp_ganado = models.IntegerField(default=0, db_column='xp_ganado')

    class Meta:
        db_table = 'practica'
        verbose_name = 'Práctica'
        constraints = [
            models.UniqueConstraint(fields=['usuario', 'sena', 'numero_intento'], name='uq_practica_usuario_sena_intento'),
            models.CheckConstraint(
                condition=models.Q(puntaje_obtenido__gte=0) & models.Q(puntaje_obtenido__lte=100), 
                name='ck_practica_puntaje_rango'
            ),
            models.CheckConstraint(condition=models.Q(xp_ganado__gte=0), name='ck_practica_xp_no_negativo'),
        ]