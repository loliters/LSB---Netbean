"""Reglas de negocio de usuarios: registro, recuperación y resumen del panel."""
import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Callable

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Nivel, Rol

from .models import EstadisticasUsuario, TokenRecuperacion, Usuario

logger = logging.getLogger(__name__)


def _minutos_token() -> int:
    return getattr(settings, "TOKEN_RECUPERACION_MINUTOS", 30)


def hashear_token(token: str) -> str:
    """Devuelve el SHA-256 del token; en BD nunca se guarda el token plano."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@transaction.atomic
def registrar_estudiante(form) -> Usuario:
    """Crea el usuario con rol Estudiante y su fila de estadísticas (HU-02, CA3)."""
    rol, _ = Rol.objects.get_or_create(nombre_rol="Estudiante")
    usuario = form.save(commit=False)
    usuario.rol = rol
    usuario.save()
    EstadisticasUsuario.objects.create(usuario=usuario)
    return usuario


@transaction.atomic
def solicitar_recuperacion(correo: str, construir_url: Callable[[str], str]) -> str | None:
    """Genera un token de 30 minutos y envía el enlace por correo (HU-12).

    Args:
        correo: Correo ya validado en formato.
        construir_url: Función que convierte una ruta relativa en URL absoluta.

    Returns:
        El token plano (solo para pruebas) o None si el correo no existe.
    """
    usuario = Usuario.objects.filter(correo__iexact=correo, estado=True).first()
    if usuario is None:
        return None
    TokenRecuperacion.objects.filter(usuario=usuario, usado=False).update(usado=True)
    token = secrets.token_urlsafe(32)
    TokenRecuperacion.objects.create(
        usuario=usuario,
        token_hash=hashear_token(token),
        fecha_expiracion=timezone.now() + timedelta(minutes=_minutos_token()),
    )
    enlace = construir_url(reverse("usuarios:restablecer_password", args=[token]))
    send_mail(
        subject="Restablece tu contraseña de Net Bean",
        message=(
            f"Hola {usuario.nombre}:\n\n"
            f"Usa este enlace para crear una nueva contraseña:\n{enlace}\n\n"
            f"El enlace vence en {_minutos_token()} minutos. "
            "Si no pediste el cambio, ignora este correo."
        ),
        from_email=None,
        recipient_list=[usuario.correo],
    )
    logger.info("Token de recuperación generado para usuario %s", usuario.pk)
    return token


def obtener_token_vigente(token: str) -> TokenRecuperacion | None:
    """Devuelve el registro del token si existe, no se usó y no expiró."""
    registro = (
        TokenRecuperacion.objects.select_related("usuario")
        .filter(token_hash=hashear_token(token))
        .first()
    )
    if registro is None or not registro.esta_vigente():
        return None
    return registro


@transaction.atomic
def restablecer_contrasena(token: str, nueva_contrasena: str) -> bool:
    """Cambia la contraseña y marca el token como usado (un solo uso)."""
    registro = (
        TokenRecuperacion.objects.select_for_update()
        .select_related("usuario")
        .filter(token_hash=hashear_token(token))
        .first()
    )
    if registro is None or not registro.esta_vigente():
        return False
    registro.usuario.set_password(nueva_contrasena)
    registro.usuario.save(update_fields=["password"])
    registro.usado = True
    registro.save(update_fields=["usado"])
    return True


def resumen_estudiante(usuario: Usuario) -> dict:
    """Datos del panel del estudiante: XP, nivel, racha y próximo logro."""
    from apps.gamificacion.models import Logro
    from apps.progreso.models import ProgresoLeccion

    estadisticas, _ = EstadisticasUsuario.objects.get_or_create(usuario=usuario)
    xp = estadisticas.xp_total
    nivel = Nivel.objects.filter(xp_requerido__lte=xp).order_by("-xp_requerido").first()
    siguiente = Nivel.objects.filter(xp_requerido__gt=xp).order_by("xp_requerido").first()
    porcentaje_nivel = 100
    if siguiente:
        base = nivel.xp_requerido if nivel else 0
        porcentaje_nivel = round((xp - base) / max(siguiente.xp_requerido - base, 1) * 100)
    return {
        "estadisticas": estadisticas,
        "nivel": nivel,
        "siguiente_nivel": siguiente,
        "xp_faltante": (siguiente.xp_requerido - xp) if siguiente else 0,
        "porcentaje_nivel": porcentaje_nivel,
        "lecciones_completadas": ProgresoLeccion.objects.filter(
            usuario=usuario, fecha_completado__isnull=False
        ).count(),
        "proximo_logro": Logro.objects.exclude(usuariologro__usuario=usuario)
        .order_by("meta_valor")
        .first(),
    }
