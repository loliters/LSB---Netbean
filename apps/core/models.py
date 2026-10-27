from django.db import models

class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True, db_column='id_rol')
    nombre_rol = models.CharField(max_length=50, unique=True, db_column='nombre_rol')

    class Meta:
        db_table = 'rol'
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    def __str__(self):
        return self.nombre_rol


class Nivel(models.Model):
    id_nivel = models.AutoField(primary_key=True, db_column='id_nivel')
    numero_nivel = models.IntegerField(unique=True, db_column='numero_nivel')
    nombre_nivel = models.CharField(max_length=50, db_column='nombre_nivel')
    xp_requerido = models.IntegerField(unique=True, db_column='xp_requerido')

    class Meta:
        db_table = 'nivel'
        verbose_name = 'Nivel'
        verbose_name_plural = 'Niveles'
        constraints = [
            models.CheckConstraint(condition=models.Q(xp_requerido__gte=0), name='ck_nivel_xp_no_negativo')
        ]

    def __str__(self):
        return f"Nivel {self.numero_nivel}: {self.nombre_nivel}"


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True, db_column='id_categoria')
    nombre = models.CharField(max_length=50, unique=True, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    activo = models.BooleanField(default=True, db_column='activo')

    class Meta:
        db_table = 'categoria'
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'

    def __str__(self):
        return self.nombre


class TipoSena(models.Model):
    id_tipo_sena = models.AutoField(primary_key=True, db_column='id_tipo_sena')
    nombre = models.CharField(max_length=50, unique=True, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')

    class Meta:
        db_table = 'tipo_sena'
        verbose_name = 'Tipo de Seña'
        verbose_name_plural = 'Tipos de Seña'

    def __str__(self):
        return self.nombre


class Dificultad(models.Model):
    id_dificultad = models.AutoField(primary_key=True, db_column='id_dificultad')
    nivel = models.IntegerField(unique=True, db_column='nivel')
    nombre = models.CharField(max_length=50, db_column='nombre')
    multiplicador_xp = models.DecimalField(max_digits=4, decimal_places=2, db_column='multiplicador_xp')

    class Meta:
        db_table = 'dificultad'
        verbose_name = 'Dificultad'
        verbose_name_plural = 'Dificultades'
        constraints = [
            models.CheckConstraint(condition=models.Q(multiplicador_xp__gt=0), name='ck_dificultad_multiplicador_positivo')
        ]

    def __str__(self):
        return self.nombre


class TipoLogro(models.Model):
    id_tipo_logro = models.AutoField(primary_key=True, db_column='id_tipo_logro')
    nombre = models.CharField(max_length=50, unique=True, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    metrica = models.CharField(
        max_length=20, db_column='metrica',
        choices=[('practicas', 'Prácticas'), ('racha', 'Racha'), ('dominadas', 'Dominadas'), ('nivel', 'Nivel')]
    )

    class Meta:
        db_table = 'tipo_logro'
        verbose_name = 'Tipo de Logro'
        verbose_name_plural = 'Tipos de Logro'
        constraints = [
            models.CheckConstraint(
                condition=models.Q(metrica__in=['practicas', 'racha', 'dominadas', 'nivel']),
                name='ck_tipo_logro_metrica_valida'
            )
        ]

    def __str__(self):
        return self.nombre


class EstadoProgreso(models.Model):
    id_estado = models.AutoField(primary_key=True, db_column='id_estado')
    nombre = models.CharField(max_length=20, unique=True, db_column='nombre')
    descripcion = models.TextField(blank=True, null=True, db_column='descripcion')
    color = models.CharField(max_length=7, blank=True, null=True, db_column='color')

    class Meta:
        db_table = 'estado_progreso'
        verbose_name = 'Estado de Progreso'
        verbose_name_plural = 'Estados de Progreso'

    def __str__(self):
        return self.nombre