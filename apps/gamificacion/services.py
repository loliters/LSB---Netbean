"""Reglas de gamificación: intentos, XP y racha (HU-06, HU-07)."""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.models import EstadoProgreso
from apps.progreso.models import Practica, ProgresoLeccion, ProgresoSena
from apps.usuarios.models import EstadisticasUsuario


def xp_por_acierto() -> int:
    return getattr(settings, "XP_POR_ACIERTO", 30)


def normalizar_letra(texto: str | None) -> str:
    return (texto or "").strip().upper()


def a_puntaje(confianza: float) -> Decimal:
    """Convierte la confianza (0-1) en puntaje porcentual con 2 decimales."""
    acotada = min(max(float(confianza or 0), 0.0), 1.0)
    return Decimal(str(round(acotada * 100, 2)))


def calcular_racha(racha_actual: int, ultima_practica: date | None, hoy: date) -> int:
    """Mismo día: se mantiene. Día siguiente: +1. Hueco mayor: reinicia en 1."""
    if ultima_practica == hoy:
        return max(racha_actual, 1)
    if ultima_practica == hoy - timedelta(days=1):
        return racha_actual + 1
    return 1


def _en_enfriamiento(usuario, sena) -> bool:
    segundos = getattr(settings, "XP_ENFRIAMIENTO_SEGUNDOS", 0)
    if not segundos:
        return False
    desde = timezone.now() - timedelta(seconds=segundos)
    return Practica.objects.filter(
        usuario=usuario, sena=sena, xp_ganado__gt=0, fecha_practica__gte=desde
    ).exists()


def _estado(nombre: str) -> EstadoProgreso:
    """Obtiene (o crea) un estado de progreso por nombre, sin distinguir mayúsculas."""
    estado = EstadoProgreso.objects.filter(nombre__iexact=nombre).first()
    return estado or EstadoProgreso.objects.create(nombre=nombre)


def actualizar_leccion(usuario, leccion) -> dict:
    """Marca la lección como completada cuando todas sus señas están dominadas."""
    total = leccion.senas.filter(estado=True).count()
    dominadas = ProgresoSena.objects.filter(
        usuario=usuario, sena__leccion=leccion, sena__estado=True, dominada=True
    ).count()
    progreso, _ = ProgresoLeccion.objects.get_or_create(
        usuario=usuario, leccion=leccion, defaults={"estado": _estado("En progreso")}
    )
    completada = total > 0 and dominadas >= total
    if completada and progreso.fecha_completado is None:
        progreso.estado = _estado("Completado")
        progreso.fecha_completado = timezone.now()
        progreso.save(update_fields=["estado", "fecha_completado"])
    return {
        "senas_dominadas": dominadas,
        "total_senas": total,
        "leccion_completada": progreso.fecha_completado is not None,
    }


@transaction.atomic
def registrar_intento(*, usuario, sena, letra_predicha: str | None, confianza: float) -> dict:
    """Guarda el intento en ``practica``; el Signal aplica XP y racha.

    Un intento es correcto si la letra coincide y el puntaje alcanza
    ``sena.puntos_minimos``. Un acierto deja la seña como dominada.

    Returns:
        Resultado del intento, estadísticas y avance de la lección.
    """
    puntaje = a_puntaje(confianza)
    letra_coincide = normalizar_letra(letra_predicha) == normalizar_letra(sena.nombre)
    es_correcta = letra_coincide and puntaje >= sena.puntos_minimos
    progreso, _ = ProgresoSena.objects.select_for_update().get_or_create(usuario=usuario, sena=sena)
    ultimo = Practica.objects.filter(usuario=usuario, sena=sena).aggregate(m=Max("numero_intento"))["m"]
    xp = xp_por_acierto() if es_correcta and not _en_enfriamiento(usuario, sena) else 0
    practica = Practica.objects.create(
        usuario=usuario,
        sena=sena,
        numero_intento=(ultimo or 0) + 1,
        puntaje_obtenido=puntaje,
        xp_ganado=xp,
    )
    progreso.intentos += 1
    if letra_coincide:
        progreso.mejor_puntaje = max(progreso.mejor_puntaje, puntaje)
    progreso.dominada = progreso.dominada or es_correcta
    progreso.save()
    estadisticas = EstadisticasUsuario.objects.get(usuario=usuario)
    return {
        "es_correcta": es_correcta,
        "letra_coincide": letra_coincide,
        "puntaje": float(puntaje),
        "puntos_minimos": sena.puntos_minimos,
        "xp_ganado": practica.xp_ganado,
        "numero_intento": practica.numero_intento,
        "dominada": progreso.dominada,
        "xp_total": estadisticas.xp_total,
        "racha_dias": estadisticas.racha_dias,
        "total_practicas": estadisticas.total_practicas,
        **actualizar_leccion(usuario, sena.leccion),
    }

@transaction.atomic
def aplicar_recompensa(practica: Practica) -> EstadisticasUsuario:
    """Suma XP, práctica y racha de forma persistente y con bloqueo de fila."""
    estadisticas, _ = EstadisticasUsuario.objects.select_for_update().get_or_create(
        usuario_id=practica.usuario_id
    )
    estadisticas.total_practicas += 1
    campos = ["total_practicas"]
    if practica.xp_ganado > 0:
        hoy = timezone.localdate()
        estadisticas.xp_total += practica.xp_ganado
        estadisticas.racha_dias = calcular_racha(
            estadisticas.racha_dias, estadisticas.ultima_practica, hoy
        )
        estadisticas.ultima_practica = hoy
        campos += ["xp_total", "racha_dias", "ultima_practica"]
    estadisticas.save(update_fields=campos)
    return estadisticas
