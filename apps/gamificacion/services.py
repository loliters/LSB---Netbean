"""Reglas de gamificación: intentos, XP y racha (HU-06, HU-07)."""
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from apps.core.models import EstadoProgreso, Nivel
from apps.progreso.models import Practica, ProgresoLeccion, ProgresoSena
from apps.usuarios.asignaciones import alcance_contenido
from apps.usuarios.models import EstadisticasUsuario

from .models import Logro, UsuarioLogro


def xp_por_acierto() -> int:
    return getattr(settings, "XP_POR_ACIERTO", 30)


def umbral_efectivo(sena) -> int:
    """Porcentaje mínimo para aprobar: el de la seña, con tope en ``PRACTICA_UMBRAL_AUTO``."""
    tope = getattr(settings, "PRACTICA_UMBRAL_AUTO", 70)
    return min(sena.puntos_minimos, tope)


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
    """Marca la lección como completada cuando todas sus señas (las que ve el estudiante) están dominadas."""
    alcance = alcance_contenido(usuario)
    senas = leccion.senas.filter(estado=True)
    logradas = ProgresoSena.objects.filter(
        usuario=usuario, sena__leccion=leccion, sena__estado=True, dominada=True
    )
    if alcance is not None:
        senas = senas.filter(pk__in=alcance.senas)
        logradas = logradas.filter(sena_id__in=alcance.senas)
    total = senas.count()
    dominadas = logradas.count()
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

    Una seña ya dominada se puede repasar cuantas veces se quiera, pero el
    repaso no suma XP ni racha (``repaso=True`` en el resultado).

    Returns:
        Resultado del intento, estadísticas y avance de la lección.
    """
    inicio = timezone.now()
    puntaje = a_puntaje(confianza)
    letra_coincide = normalizar_letra(letra_predicha) == normalizar_letra(sena.nombre)
    es_correcta = letra_coincide and puntaje >= umbral_efectivo(sena)
    progreso, _ = ProgresoSena.objects.select_for_update().get_or_create(usuario=usuario, sena=sena)
    ya_dominada = progreso.dominada  # se lee antes de actualizar: decide si este intento da XP
    ultimo = Practica.objects.filter(usuario=usuario, sena=sena).aggregate(m=Max("numero_intento"))["m"]
    da_xp = es_correcta and not ya_dominada and not _en_enfriamiento(usuario, sena)
    xp = xp_por_acierto() if da_xp else 0
    practica = Practica.objects.create(
        usuario=usuario,
        sena=sena,
        numero_intento=(ultimo or 0) + 1,
        puntaje_obtenido=puntaje,
        xp_ganado=xp,
        es_correcta=es_correcta,
    )
    progreso.intentos += 1
    if letra_coincide:
        progreso.mejor_puntaje = max(progreso.mejor_puntaje, puntaje)
    progreso.dominada = progreso.dominada or es_correcta
    progreso.save()
    leccion = actualizar_leccion(usuario, sena.leccion)
    estadisticas = EstadisticasUsuario.objects.select_for_update().get(usuario=usuario)
    evaluar_logros(usuario, estadisticas)  # segunda pasada: ya cuenta la seña recién dominada
    nuevos = UsuarioLogro.objects.filter(usuario=usuario, fecha_obtencion__gte=inicio).select_related("logro")
    return {
        "es_correcta": es_correcta,
        "repaso": ya_dominada,
        "letra_coincide": letra_coincide,
        "puntaje": float(puntaje),
        "puntos_minimos": umbral_efectivo(sena),
        "xp_ganado": practica.xp_ganado,
        "numero_intento": practica.numero_intento,
        "dominada": progreso.dominada,
        "xp_total": estadisticas.xp_total,
        "racha_dias": estadisticas.racha_dias,
        "total_practicas": estadisticas.total_practicas,
        "logros_nuevos": [
            {"nombre": u.logro.nombre, "icono": u.logro.icono or "award-fill", "xp_bonus": u.logro.xp_bonus}
            for u in nuevos
        ],
        **leccion,
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
    evaluar_logros(practica.usuario, estadisticas)
    return estadisticas


# ---------- Logros y niveles (HU-11) ----------
def nivel_actual(xp_total: int) -> Nivel | None:
    """Nivel más alto cuyo XP requerido ya se alcanzó."""
    return Nivel.objects.filter(xp_requerido__lte=xp_total).order_by("-xp_requerido").first()


def valores_metricas(usuario, estadisticas: EstadisticasUsuario) -> dict[str, int]:
    """Valor actual de cada métrica que miden los logros."""
    nivel = nivel_actual(estadisticas.xp_total)
    return {
        "practicas": estadisticas.total_practicas,
        "racha": estadisticas.racha_dias,
        "dominadas": ProgresoSena.objects.filter(usuario=usuario, dominada=True).count(),
        "nivel": nivel.numero_nivel if nivel else 0,
    }


def dominadas_por_modulo(usuario) -> dict[int, int]:
    """Señas dominadas por el usuario agrupadas por módulo."""
    from django.db.models import Count

    return dict(
        ProgresoSena.objects.filter(usuario=usuario, dominada=True)
        .values_list("sena__leccion__modulo_id")
        .annotate(total=Count("pk"))
    )


def valor_de(logro: Logro, valores: dict[str, int], por_modulo: dict[int, int]) -> int:
    """Valor actual de la métrica de un logro; los de módulo cuentan solo sus señas."""
    if logro.modulo_id and logro.tipo_logro.metrica == "dominadas":
        return por_modulo.get(logro.modulo_id, 0)
    return valores.get(logro.tipo_logro.metrica, 0)


@transaction.atomic
def evaluar_logros(usuario, estadisticas: EstadisticasUsuario) -> list[Logro]:
    """Otorga los logros cuya meta se cumplió y suma su XP extra.

    Es idempotente: la restricción UNIQUE (usuario, logro) impide otorgar dos veces.
    Repite la evaluación porque el XP extra puede subir de nivel y abrir otro logro.
    """
    nuevos: list[Logro] = []
    for _ in range(5):
        obtenidos = UsuarioLogro.objects.filter(usuario=usuario).values_list("logro_id", flat=True)
        valores = valores_metricas(usuario, estadisticas)
        por_modulo = dominadas_por_modulo(usuario)
        cumplidos = [
            logro
            for logro in Logro.objects.select_related("tipo_logro").exclude(pk__in=list(obtenidos))
            if valor_de(logro, valores, por_modulo) >= logro.meta_valor
        ]
        if not cumplidos:
            break
        for logro in cumplidos:
            _, creado = UsuarioLogro.objects.get_or_create(usuario=usuario, logro=logro)
            if creado:
                estadisticas.xp_total += logro.xp_bonus
                nuevos.append(logro)
        estadisticas.save(update_fields=["xp_total"])
    return nuevos


def progreso_logros(usuario) -> list[dict]:
    """Logros con su avance para la pantalla «Mis logros»."""
    estadisticas, _ = EstadisticasUsuario.objects.get_or_create(usuario=usuario)
    valores = valores_metricas(usuario, estadisticas)
    por_modulo = dominadas_por_modulo(usuario)
    obtenidos = {u.logro_id: u.fecha_obtencion for u in UsuarioLogro.objects.filter(usuario=usuario)}
    resultado = []
    for logro in Logro.objects.select_related("tipo_logro", "modulo").order_by("tipo_logro__nombre", "meta_valor"):
        actual = min(valor_de(logro, valores, por_modulo), logro.meta_valor)
        resultado.append({
            "logro": logro,
            "obtenido": logro.pk in obtenidos,
            "fecha": obtenidos.get(logro.pk),
            "actual": actual,
            "porcentaje": round(actual / logro.meta_valor * 100),
        })
    resultado.sort(key=lambda item: (not item["obtenido"], -item["porcentaje"]))
    return resultado
