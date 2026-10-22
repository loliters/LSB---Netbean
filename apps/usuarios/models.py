"""Modelos de usuarios, recuperación de contraseña y estadísticas.

Cambios respecto a la versión anterior (sin migración: solo métodos/propiedades):
- create_user/create_superuser aceptan ``password`` (lo que envía createsuperuser).
- create_superuser activa también ``is_superuser`` de PermissionsMixin.
- Propiedades ``is_active`` e ``is_staff`` mapeadas a ``estado`` y ``es_staff``.
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone

from apps.core.models import Rol


class UsuarioManager(BaseUserManager):
    """Gestor de usuarios autenticados por correo."""

    def create_user(self, correo, password=None, **extra_fields):
        if not correo:
            raise ValueError("El correo es obligatorio")
        password = password or extra_fields.pop("contrasena", None)
        rol = extra_fields.get("rol")
        if rol is not None and not isinstance(rol, Rol):
            extra_fields["rol"] = Rol.objects.get(pk=rol)
        usuario = self.model(correo=self.normalize_email(correo).lower(), **extra_fields)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, password=None, **extra_fields):
        extra_fields.setdefault("es_staff", True)
        extra_fields.setdefault("es_superuser", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("rol") is None:
            extra_fields["rol"], _ = Rol.objects.get_or_create(nombre_rol="Administrador")
        return self.create_user(correo, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True, db_column="id_usuario")
    rol = models.ForeignKey(Rol, on_delete=models.PROTECT, db_column="id_rol")
    nombre = models.CharField(max_length=100, db_column="nombre")
    apellido = models.CharField(max_length=100, db_column="apellido")
    correo = models.EmailField(unique=True, db_column="correo")
    password = models.CharField(max_length=255, db_column="contrasena")
    fecha_registro = models.DateTimeField(auto_now_add=True, db_column="fecha_registro")
    ultimo_acceso = models.DateTimeField(null=True, blank=True, db_column="ultimo_acceso")
    estado = models.BooleanField(default=True, db_column="estado")
    es_staff = models.BooleanField(default=False, db_column="es_staff")
    es_superuser = models.BooleanField(default=False, db_column="es_superuser")

    objects = UsuarioManager()
    USERNAME_FIELD = "correo"
    EMAIL_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre", "apellido", "rol"]

    class Meta:
        db_table = "usuario"
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(correo__iregex=r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$"),
                name="chk_correo_valido",
            )
        ]

    def __str__(self) -> str:
        return f"{self.nombre} {self.apellido} ({self.correo})"

    @property
    def is_active(self) -> bool:
        return self.estado

    @is_active.setter
    def is_active(self, valor: bool) -> None:
        self.estado = valor

    @property
    def is_staff(self) -> bool:
        return self.es_staff or self.es_superuser or self.is_superuser

    @property
    def nombre_completo(self) -> str:
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def iniciales(self) -> str:
        return f"{self.nombre[:1]}{self.apellido[:1]}".upper()

    @property
    def nombre_rol(self) -> str:
        return self.rol.nombre_rol.lower() if self.rol_id else ""


class TokenRecuperacion(models.Model):
    id_token = models.AutoField(primary_key=True, db_column="id_token")
    usuario = models.ForeignKey("usuarios.Usuario", on_delete=models.CASCADE, db_column="id_usuario")
    token_hash = models.CharField(max_length=128, unique=True, db_column="token_hash")
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column="fecha_creacion")
    fecha_expiracion = models.DateTimeField(db_column="fecha_expiracion")
    usado = models.BooleanField(default=False, db_column="usado")

    class Meta:
        db_table = "token_recuperacion"
        verbose_name = "Token de Recuperación"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(fecha_expiracion__gt=models.F("fecha_creacion")),
                name="chk_token_expiracion_valida",
            )
        ]

    def esta_vigente(self) -> bool:
        """Indica si el token no fue usado y no ha expirado."""
        return not self.usado and timezone.now() < self.fecha_expiracion


class EstadisticasUsuario(models.Model):
    id_estadistica = models.AutoField(primary_key=True, db_column="id_estadistica")
    usuario = models.OneToOneField(
        "usuarios.Usuario", on_delete=models.CASCADE, unique=True, db_column="id_usuario"
    )
    xp_total = models.IntegerField(default=0, db_column="xp_total")
    racha_dias = models.IntegerField(default=0, db_column="racha_dias")
    ultima_practica = models.DateField(null=True, blank=True, db_column="ultima_practica")
    total_practicas = models.IntegerField(default=0, db_column="total_practicas")

    class Meta:
        db_table = "estadisticas_usuario"
        verbose_name = "Estadística de Usuario"
        constraints = [
            models.CheckConstraint(condition=models.Q(xp_total__gte=0), name="ck_estadistica_xp_no_negativo"),
            models.CheckConstraint(condition=models.Q(racha_dias__gte=0), name="ck_estadistica_racha_no_negativa"),
            models.CheckConstraint(
                condition=models.Q(total_practicas__gte=0), name="ck_estadistica_practicas_no_negativas"
            ),
        ]
