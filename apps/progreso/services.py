"""Estadísticas de práctica para dashboard, perfil y panel de administración."""
from datetime import timedelta

from django.db.models import Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from .models import Practica, ProgresoLeccion, ProgresoSena

DIAS_SEMANA = ("Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom")
PAUSA_MAXIMA = timedelta(minutes=5)   # más tiempo entre intentos = otra sesión
TIEMPO_POR_INTENTO = timedelta(seconds=15)


def _por_dia(consulta, dias: int) -> list[dict]:
    hoy = timezone.localdate()
    desde = hoy - timedelta(days=dias - 1)
    filas = (
        consulta.filter(fecha_practica__date__gte=desde)
        .annotate(dia=TruncDate("fecha_practica", tzinfo=timezone.get_current_timezone()))
        .values("dia")
        .annotate(intentos=Count("pk"), aciertos=Count("pk", filter=Q(es_correcta=True)))
    )
    por_fecha = {f["dia"]: f for f in filas}
    resultado = []
    for i in range(dias):
        dia = desde + timedelta(days=i)
        fila = por_fecha.get(dia, {"intentos": 0, "aciertos": 0})
        resultado.append({"dia": dia, "etiqueta": DIAS_SEMANA[dia.weekday()] if dias <= 7 else dia.strftime("%d/%m"),
                          "intentos": fila["intentos"], "aciertos": fila["aciertos"]})
    return resultado


def actividad_semanal(usuario) -> list[dict]:
    """Intentos y aciertos de los últimos 7 días."""
    return _por_dia(Practica.objects.filter(usuario=usuario), 7)


def actividad_global(dias: int = 14) -> list[dict]:
    """Intentos y aciertos de todo el sistema."""
    return _por_dia(Practica.objects.all(), dias)


def tiempo_practica(usuario) -> timedelta:
    """Tiempo estimado: suma de pausas cortas entre intentos más 15 s por intento."""
    fechas = list(
        Practica.objects.filter(usuario=usuario).order_by("fecha_practica").values_list("fecha_practica", flat=True)[:5000]
    )
    total = TIEMPO_POR_INTENTO * len(fechas)
    for anterior, actual in zip(fechas, fechas[1:]):
        pausa = actual - anterior
        if pausa <= PAUSA_MAXIMA:
            total += pausa
    return total


def formato_duracion(duracion: timedelta) -> str:
    minutos = int(duracion.total_seconds() // 60)
    horas, resto = divmod(minutos, 60)
    if horas:
        return f"{horas} h {resto} min"
    return f"{minutos} min"


def precision(usuario) -> float:
    """Porcentaje de intentos correctos del usuario."""
    datos = Practica.objects.filter(usuario=usuario).aggregate(
        intentos=Count("pk"), aciertos=Count("pk", filter=Q(es_correcta=True))
    )
    return round(datos["aciertos"] / datos["intentos"] * 100, 1) if datos["intentos"] else 0.0


def actividad_reciente(usuario, limite: int = 8):
    return (
        Practica.objects.filter(usuario=usuario)
        .select_related("sena__leccion__modulo")
        .order_by("-fecha_practica")[:limite]
    )


def resumen_usuario(usuario) -> dict:
    """Números que comparten el dashboard y el perfil."""
    return {
        "precision": precision(usuario),
        "tiempo": formato_duracion(tiempo_practica(usuario)),
        "senas_dominadas": ProgresoSena.objects.filter(usuario=usuario, dominada=True).count(),
        "lecciones_completadas": ProgresoLeccion.objects.filter(usuario=usuario, fecha_completado__isnull=False).count(),
    }


def resumen_sistema() -> dict:
    """Métricas globales para el panel del administrador."""
    hoy = timezone.localdate()
    semana = Practica.objects.filter(fecha_practica__date__gte=hoy - timedelta(days=6))
    datos = semana.aggregate(intentos=Count("pk"), aciertos=Count("pk", filter=Q(es_correcta=True)),
                             activos=Count("usuario", distinct=True))
    return {
        "practicas_hoy": Practica.objects.filter(fecha_practica__date=hoy).count(),
        "practicas_semana": datos["intentos"],
        "activos_semana": datos["activos"],
        "precision_semana": round(datos["aciertos"] / datos["intentos"] * 100, 1) if datos["intentos"] else 0.0,
    }
