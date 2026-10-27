"""Estadísticas de aprendizaje para el reporte de progreso (HU-10).

Todas las funciones reciben FiltrosReporte y devuelven datos simples
(dict, list, int, float), listos para la vista, el Excel y el PDF.
"""
from dataclasses import dataclass
from datetime import date, timedelta

from django.db.models import Avg, Count, Max, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.progreso.models import Practica, ProgresoLeccion, ProgresoSena
from apps.usuarios.models import Usuario


@dataclass(frozen=True)
class FiltrosReporte:
    """Filtros del reporte.

    ``alcance`` limita a qué estudiantes se puede mirar: None = todos (administrador);
    una tupla de IDs = solo esos (profesor). ``estudiante`` afina a uno solo dentro del alcance.
    """

    desde: date
    hasta: date
    modulo: object | None = None       # Modulo
    estudiante: object | None = None   # Usuario
    alcance: tuple | None = None
    solo_mios: bool = False

    @property
    def descripcion(self) -> str:
        partes = [f"Del {self.desde:%d/%m/%Y} al {self.hasta:%d/%m/%Y}"]
        partes.append(f"Módulo: {self.modulo.nombre}" if self.modulo else "Todos los módulos")
        if self.estudiante:
            partes.append(f"Estudiante: {self.estudiante.nombre_completo}")
        elif self.solo_mios:
            partes.append("Mis estudiantes")
        return " · ".join(partes)


def ids_en_alcance(filtros: FiltrosReporte) -> list[int] | None:
    """IDs de estudiantes que entran en el reporte; None significa «todos»."""
    ids = None if filtros.alcance is None else set(filtros.alcance)
    if filtros.estudiante is not None:
        unico = {filtros.estudiante.pk}
        ids = unico if ids is None else ids & unico
    return None if ids is None else sorted(ids)


def estudiantes_en_alcance(filtros: FiltrosReporte):
    consulta = Usuario.objects.filter(rol__nombre_rol__iexact="estudiante", estado=True)
    ids = ids_en_alcance(filtros)
    return consulta if ids is None else consulta.filter(pk__in=ids)


def tasa(aciertos: int, intentos: int) -> float:
    """Porcentaje de acierto con un decimal."""
    return round(aciertos / intentos * 100, 1) if intentos else 0.0


def practicas(filtros: FiltrosReporte):
    consulta = Practica.objects.filter(
        fecha_practica__date__gte=filtros.desde, fecha_practica__date__lte=filtros.hasta
    )
    if filtros.modulo:
        consulta = consulta.filter(sena__leccion__modulo=filtros.modulo)
    ids = ids_en_alcance(filtros)
    if ids is not None:
        consulta = consulta.filter(usuario_id__in=ids)
    return consulta


def resumen(filtros: FiltrosReporte) -> dict:
    consulta = practicas(filtros)
    totales = consulta.aggregate(
        intentos=Count("pk"),
        aciertos=Count("pk", filter=Q(es_correcta=True)),
        xp=Sum("xp_ganado"),
        estudiantes=Count("usuario", distinct=True),
    )
    dominadas = ProgresoSena.objects.filter(dominada=True)
    lecciones = ProgresoLeccion.objects.filter(
        fecha_completado__date__gte=filtros.desde, fecha_completado__date__lte=filtros.hasta
    )
    if filtros.modulo:
        dominadas = dominadas.filter(sena__leccion__modulo=filtros.modulo)
        lecciones = lecciones.filter(leccion__modulo=filtros.modulo)
    ids = ids_en_alcance(filtros)
    if ids is not None:
        dominadas = dominadas.filter(usuario_id__in=ids)
        lecciones = lecciones.filter(usuario_id__in=ids)
    return {
        "estudiantes_registrados": estudiantes_en_alcance(filtros).count(),
        "estudiantes_activos": totales["estudiantes"],
        "intentos": totales["intentos"],
        "aciertos": totales["aciertos"],
        "tasa_acierto": tasa(totales["aciertos"], totales["intentos"]),
        "xp_otorgado": totales["xp"] or 0,
        "senas_dominadas": dominadas.count(),
        "lecciones_completadas": lecciones.count(),
    }


def por_dia(filtros: FiltrosReporte) -> list[dict]:
    """Intentos y aciertos por día, incluidos los días sin prácticas."""
    filas = (
        practicas(filtros)
        .annotate(dia=TruncDate("fecha_practica", tzinfo=timezone.get_current_timezone()))
        .values("dia")
        .annotate(intentos=Count("pk"), aciertos=Count("pk", filter=Q(es_correcta=True)))
    )
    por_fecha = {fila["dia"]: fila for fila in filas}
    resultado, dia = [], filtros.desde
    while dia <= filtros.hasta:
        fila = por_fecha.get(dia, {"intentos": 0, "aciertos": 0})
        resultado.append({"dia": dia, "intentos": fila["intentos"], "aciertos": fila["aciertos"]})
        dia += timedelta(days=1)
    return resultado


def por_sena(filtros: FiltrosReporte) -> list[dict]:
    """Rendimiento por seña, de menor a mayor acierto (las que hay que reforzar primero)."""
    filas = (
        practicas(filtros)
        .values("sena_id", "sena__nombre", "sena__leccion__modulo__nombre")
        .annotate(
            intentos=Count("pk"),
            aciertos=Count("pk", filter=Q(es_correcta=True)),
            puntaje=Avg("puntaje_obtenido"),
            estudiantes=Count("usuario", distinct=True),
        )
    )
    resultado = [
        {
            "sena": fila["sena__nombre"],
            "modulo": fila["sena__leccion__modulo__nombre"],
            "intentos": fila["intentos"],
            "aciertos": fila["aciertos"],
            "tasa": tasa(fila["aciertos"], fila["intentos"]),
            "puntaje_promedio": round(float(fila["puntaje"] or 0), 1),
            "estudiantes": fila["estudiantes"],
        }
        for fila in filas
    ]
    return sorted(resultado, key=lambda f: (f["tasa"], -f["intentos"]))


def por_estudiante(filtros: FiltrosReporte) -> list[dict]:
    """Ranking de estudiantes por XP ganado en el periodo."""
    filas = (
        practicas(filtros)
        .values(
            "usuario_id", "usuario__nombre", "usuario__apellido", "usuario__correo",
            "usuario__estadisticasusuario__racha_dias", "usuario__estadisticasusuario__xp_total",
        )
        .annotate(
            intentos=Count("pk"),
            aciertos=Count("pk", filter=Q(es_correcta=True)),
            xp=Sum("xp_ganado"),
            ultima=Max("fecha_practica"),
        )
    )
    propias = ProgresoSena.objects.filter(dominada=True)
    ids = ids_en_alcance(filtros)
    if ids is not None:
        propias = propias.filter(usuario_id__in=ids)
    dominadas = dict(propias.values_list("usuario_id").annotate(total=Count("pk")))
    resultado = [
        {
            "nombre": f"{fila['usuario__nombre']} {fila['usuario__apellido']}",
            "correo": fila["usuario__correo"],
            "intentos": fila["intentos"],
            "aciertos": fila["aciertos"],
            "tasa": tasa(fila["aciertos"], fila["intentos"]),
            "xp_periodo": fila["xp"] or 0,
            "xp_total": fila["usuario__estadisticasusuario__xp_total"] or 0,
            "racha": fila["usuario__estadisticasusuario__racha_dias"] or 0,
            "dominadas": dominadas.get(fila["usuario_id"], 0),
            "ultima": timezone.localtime(fila["ultima"]) if fila["ultima"] else None,
        }
        for fila in filas
    ]
    return sorted(resultado, key=lambda f: (-f["xp_periodo"], -f["tasa"]))


def sin_actividad(filtros: FiltrosReporte) -> list[dict]:
    """Estudiantes del alcance que no practicaron en el periodo."""
    con_practica = set(practicas(filtros).values_list("usuario_id", flat=True).distinct())
    return [
        {"nombre": u.nombre_completo, "correo": u.correo, "id": u.pk}
        for u in estudiantes_en_alcance(filtros).exclude(pk__in=con_practica).order_by("apellido", "nombre")
    ]


def construir_reporte(filtros: FiltrosReporte) -> dict:
    return {
        "filtros": filtros,
        "generado": timezone.localtime(),
        "resumen": resumen(filtros),
        "por_dia": por_dia(filtros),
        "por_sena": por_sena(filtros),
        "por_estudiante": por_estudiante(filtros),
        "sin_actividad": sin_actividad(filtros),
    }


def datos_graficos(reporte: dict, limite_senas: int = 10) -> dict:
    """Datos serializables para Chart.js."""
    senas = reporte["por_sena"][:limite_senas]
    resumen_ = reporte["resumen"]
    return {
        "dias": [f["dia"].strftime("%d/%m") for f in reporte["por_dia"]],
        "intentos": [f["intentos"] for f in reporte["por_dia"]],
        "aciertos": [f["aciertos"] for f in reporte["por_dia"]],
        "senas": [f["sena"] for f in senas],
        "tasas": [f["tasa"] for f in senas],
        "resultado": [resumen_["aciertos"], resumen_["intentos"] - resumen_["aciertos"]],
    }
