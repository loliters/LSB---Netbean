"""Reglas de negocio de usuarios: registro, recuperación y resumen del panel."""
import hashlib
import logging
import secrets
from datetime import timedelta
from typing import Callable

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template.loader import render_to_string
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
def _crear_token(correo: str) -> tuple[Usuario, str] | None:
    """Invalida los tokens anteriores y crea uno nuevo de 30 minutos. None si el correo no existe."""
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
    return usuario, token


def _enlace_de_recuperacion(token: str, construir_url: Callable[[str], str]) -> str:
    """URL absoluta del enlace. Si existe SITE_URL (.env) se usa ese dominio, útil para abrirlo desde el celular."""
    ruta = reverse("usuarios:restablecer_password", args=[token])
    base = getattr(settings, "SITE_URL", "").strip().rstrip("/")
    return f"{base}{ruta}" if base else construir_url(ruta)


def enviar_correo_recuperacion(usuario: Usuario, enlace: str) -> bool:
    """Envía el correo (texto + HTML). Devuelve False y registra el error si no se pudo enviar."""
    contexto = {"nombre": usuario.nombre, "enlace": enlace, "minutos": _minutos_token()}
    mensaje = EmailMultiAlternatives(
        subject="Restablece tu contraseña de Net Bean",
        body=render_to_string("usuarios/correo/recuperar.txt", contexto),
        from_email=None,  # usa DEFAULT_FROM_EMAIL
        to=[usuario.correo],
    )
    mensaje.attach_alternative(render_to_string("usuarios/correo/recuperar.html", contexto), "text/html")
    try:
        mensaje.send(fail_silently=False)
    except Exception:  # SMTP, red, credenciales: la persona recibe el mismo mensaje genérico
        logger.exception(
            "No se pudo enviar el correo de recuperación (usuario %s, backend %s)",
            usuario.pk, settings.EMAIL_BACKEND,
        )
        return False
    return True


def solicitar_recuperacion(correo: str, construir_url: Callable[[str], str]) -> str | None:
    """Genera un token de 30 minutos y envía el enlace por correo (HU-12).

    Args:
        correo: Correo ya validado en formato.
        construir_url: Función que convierte una ruta relativa en URL absoluta.

    Returns:
        El token plano (solo para pruebas) o None si el correo no existe. Nunca lanza
        errores de envío: se registran en el log y la respuesta al usuario es siempre la misma,
        para no revelar qué correos están registrados.
    """
    creado = _crear_token(correo)
    if creado is None:
        return None
    usuario, token = creado
    enviado = enviar_correo_recuperacion(usuario, _enlace_de_recuperacion(token, construir_url))
    logger.info("Recuperación de contraseña: usuario %s, correo %s", usuario.pk, "enviado" if enviado else "NO enviado")
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
