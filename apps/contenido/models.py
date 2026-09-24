from django.db import models


class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True, db_column='id_categoria')
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'categoria'
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self) -> str:
        return self.nombre


class Modulo(models.Model):
    id_modulo = models.AutoField(primary_key=True, db_column='id_modulo')
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        db_column='id_categoria',
        related_name='modulos',
    )
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    orden = models.PositiveIntegerField()
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'modulo'
        ordering = ['categoria', 'orden']
        constraints = [
            models.UniqueConstraint(
                fields=['categoria', 'orden'],
                name='uq_modulo_categoria_orden',
            ),
            models.CheckConstraint(
                condition=models.Q(orden__gt=0),
                name='ck_modulo_orden_positivo',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.categoria.nombre} – {self.nombre}'