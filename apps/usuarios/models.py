from django.contrib.auth.models import AbstractUser
from django.db import models


class Usuario(AbstractUser):
    """Modelo de usuario personalizado con roles."""

    class Rol(models.TextChoices):
        ESTUDIANTE = 'ESTUDIANTE', 'Estudiante'
        PROFESOR = 'PROFESOR', 'Profesor'
        ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'

    correo = models.EmailField(unique=True, db_column='correo')
    rol = models.CharField(
        max_length=20,
        choices=Rol.choices,
        default=Rol.ESTUDIANTE,
        db_column='rol',
    )

    class Meta:
        db_table = 'usuario'
        verbose_name = 'usuario'
        verbose_name_plural = 'usuarios'

    def __str__(self) -> str:
        return f'{self.username} ({self.get_rol_display()})'

    @property
    def es_estudiante(self) -> bool:
        return self.rol == self.Rol.ESTUDIANTE

    @property
    def es_profesor(self) -> bool:
        return self.rol == self.Rol.PROFESOR

    @property
    def es_administrador(self) -> bool:
        return self.rol == self.Rol.ADMINISTRADOR