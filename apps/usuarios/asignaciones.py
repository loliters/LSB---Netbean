"""Relación profesor–estudiante y asignación de contenido (HU-13).

Reglas:
- Un profesor monitorea solo a los estudiantes que se asignó (o que el administrador le asignó).
- Un estudiante puede tener varios profesores.
- Contenido visible del estudiante: sin asignaciones activas ve todo el contenido activo;
  con una o más ve únicamente lo asignado (módulo, lección o seña).
- Toda decisión de permisos se toma aquí, en el servidor; la interfaz solo la refleja.
"""
from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Max, Q
from django.utils import timezone

from apps.contenido.models import Leccion, Modulo, Sena
from apps.progreso.models import Practica, ProgresoSena

from .models import AsignacionContenido, AsignacionProfesor, Usuario

DIAS_SIN_ACTIVIDAD = 7
MODELOS_OBJETIVO = {"m": ("modulo", Modulo), "l": ("leccion", Leccion), "s": ("sena", Sena)}


# ---------------------------------------------------------------- usuarios
def estudiantes_activos():
    return Usuario.objects.filter(rol__nombre_rol__iexact="estudiante", estado=True)


def profesores_activos():
    return Usuario.objects.filter(rol__nombre_rol__iexact="profesor", estado=True)


def mis_estudiantes(profesor):
    """Estudiantes activos con una asignación activa a este profesor."""
    return estudiantes_activos().filter(
        asignaciones_como_estudiante__profesor=profesor,
        asignaciones_como_estudiante__activo=True,
    ).distinct()


def ids_de_mis_estudiantes(profesor) -> list[int]:
    return list(mis_estudiantes(profesor).values_list("pk", flat=True))


def es_estudiante_de(profesor, id_estudiante: int) -> bool:
    return mis_estudiantes(profesor).filter(pk=id_estudiante).exists()


# ------------------------------------------------- profesor ↔ estudiante
@transaction.atomic
def asignar_estudiantes(profesor, ids_estudiantes, asignado_por=None) -> int:
    """Asigna estudiantes a un profesor. Ignora a quien no sea estudiante activo.

    Returns:
        Cantidad de asignaciones nuevas o reactivadas.
    """
    if profesor.nombre_rol != "profesor":
        raise ValueError("Solo un profesor puede tener estudiantes asignados.")
    autor = asignado_por or profesor
    nuevas = 0
    for estudiante in estudiantes_activos().filter(pk__in=list(ids_estudiantes)):
        asignacion, creada = AsignacionProfesor.objects.get_or_create(
            profesor=profesor, estudiante=estudiante, defaults={"asignado_por": autor}
        )
        if creada:
            nuevas += 1
        elif not asignacion.activo:
            asignacion.activo = True
            asignacion.asignado_por = autor
            asignacion.save(update_fields=["activo", "asignado_por"])
            nuevas += 1
    return nuevas


@transaction.atomic
def quitar_estudiantes(profesor, ids_estudiantes) -> int:
    """Desactiva la asignación y el contenido que ese profesor había asignado a cada estudiante."""
    ids = list(ids_estudiantes)
    quitadas = AsignacionProfesor.objects.filter(
        profesor=profesor, estudiante_id__in=ids, activo=True
    ).update(activo=False)
    AsignacionContenido.objects.filter(profesor=profesor, estudiante_id__in=ids, activo=True).update(activo=False)
    return quitadas


@transaction.atomic
def sincronizar_estudiantes(profesor, ids_seleccionados, asignado_por) -> tuple[int, int]:
    """Deja asignados exactamente los estudiantes seleccionados (uso del administrador).

    Returns:
        (agregados, quitados)
    """
    seleccion = {int(i) for i in ids_seleccionados}
    actuales = set(mis_estudiantes(profesor).values_list("pk", flat=True))
    agregados = asignar_estudiantes(profesor, seleccion - actuales, asignado_por)
    quitados = quitar_estudiantes(profesor, actuales - seleccion)
    return agregados, quitados


# ------------------------------------------------------ asignar contenido
def decodificar_objetivo(valor: str) -> tuple[str, int]:
    """«m:3» → ("modulo", 3). Acepta m (módulo), l (lección) y s (seña)."""
    try:
        letra, numero = valor.split(":", 1)
        tipo, _ = MODELOS_OBJETIVO[letra]
        return tipo, int(numero)
    except (ValueError, KeyError, AttributeError):
        raise ValueError("El contenido elegido no es válido.") from None


@transaction.atomic
def asignar_contenido(profesor, ids_estudiantes, tipo: str, id_objetivo: int) -> int:
    """Asigna un módulo, lección o seña a los estudiantes que sean de este profesor.

    Returns:
        Cantidad de asignaciones nuevas o reactivadas.
    """
    modelo = {nombre: clase for nombre, clase in MODELOS_OBJETIVO.values()}.get(tipo)
    if modelo is None:
        raise ValueError("El tipo de contenido no es válido.")
    objetivo = modelo.objects.filter(pk=id_objetivo, estado=True).first()
    if objetivo is None:
        raise ValueError("El contenido elegido no existe o está inactivo.")
    propios = set(ids_de_mis_estudiantes(profesor)) & {int(i) for i in ids_estudiantes}
    nuevas = 0
    for id_estudiante in propios:
        asignacion, creada = AsignacionContenido.objects.get_or_create(
            profesor=profesor, estudiante_id=id_estudiante, **{tipo: objetivo}
        )
        if creada:
            nuevas += 1
        elif not asignacion.activo:
            asignacion.activo = True
            asignacion.save(update_fields=["activo"])
            nuevas += 1
    return nuevas


def quitar_contenido(profesor, id_asignacion: int) -> bool:
    """Desactiva una asignación de contenido, solo si la hizo este profesor."""
    return AsignacionContenido.objects.filter(
        pk=id_asignacion, profesor=profesor, activo=True
    ).update(activo=False) > 0


def contenido_asignado_por(profesor):
    """Asignaciones activas del profesor, listas para mostrar en una tabla."""
    return (
        AsignacionContenido.objects.filter(profesor=profesor, activo=True, estudiante__estado=True)
        .select_related("estudiante", "modulo", "leccion__modulo", "sena__leccion")
        .order_by("estudiante__apellido", "estudiante__nombre", "-fecha_asignacion")
    )


def modulos_asignados_por(profesor) -> set[int]:
    """IDs de los módulos a los que apuntan las asignaciones del profesor (directa o indirectamente)."""
    filas = AsignacionContenido.objects.filter(profesor=profesor, activo=True).values_list(
        "modulo_id", "leccion__modulo_id", "sena__leccion__modulo_id"
    )
    return {modulo for fila in filas for modulo in fila if modulo}


# -------------------------------------------- contenido visible del estudiante
@dataclass(frozen=True)
class Alcance:
    """Contenido activo que un estudiante puede ver y practicar."""

    modulos: frozenset
    lecciones: frozenset
    senas: frozenset


def alcance_contenido(usuario) -> Alcance | None:
    """Alcance del estudiante, o None si ve todo (sin asignaciones, o no es estudiante)."""
    if usuario is None or not getattr(usuario, "is_authenticated", False) or usuario.nombre_rol != "estudiante":
        return None
    filas = list(
        AsignacionContenido.objects.filter(estudiante=usuario, activo=True).values_list(
            "modulo_id", "leccion_id", "sena_id"
        )
    )
    if not filas:
        return None
    modulos = {m for m, _, _ in filas if m}
    lecciones = {le for _, le, _ in filas if le}
    senas = {s for _, _, s in filas if s}
    visibles = Sena.objects.filter(
        estado=True, leccion__estado=True, leccion__modulo__estado=True
    ).filter(Q(leccion__modulo__in=modulos) | Q(leccion__in=lecciones) | Q(pk__in=senas))
    ids_senas = set(visibles.values_list("pk", flat=True))
    ids_lecciones = (
        set(visibles.values_list("leccion_id", flat=True))
        | set(Leccion.objects.filter(pk__in=lecciones, estado=True).values_list("pk", flat=True))
        | set(Leccion.objects.filter(modulo_id__in=modulos, estado=True).values_list("pk", flat=True))
    )
    ids_modulos = set(modulos) | set(
        Leccion.objects.filter(pk__in=ids_lecciones).values_list("modulo_id", flat=True)
    )
    return Alcance(frozenset(ids_modulos), frozenset(ids_lecciones), frozenset(ids_senas))


def puede_ver_sena(usuario, sena) -> bool:
    alcance = alcance_contenido(usuario)
    return alcance is None or sena.pk in alcance.senas


# ------------------------------------------------------ monitoreo (panel)
def avance_estudiantes(profesor) -> list[dict]:
    """Avance de cada estudiante del profesor: dominio, acierto y última actividad."""
    estudiantes = list(mis_estudiantes(profesor).order_by("apellido", "nombre"))
    ids = [e.pk for e in estudiantes]
    practicas = {
        fila["usuario_id"]: fila
        for fila in Practica.objects.filter(usuario_id__in=ids).values("usuario_id").annotate(
            intentos=Count("pk"), aciertos=Count("pk", filter=Q(es_correcta=True)), ultima=Max("fecha_practica")
        )
    }
    dominadas = dict(
        ProgresoSena.objects.filter(usuario_id__in=ids, dominada=True)
        .values_list("usuario_id").annotate(total=Count("pk"))
    )
    con_asignacion = set(
        AsignacionContenido.objects.filter(estudiante_id__in=ids, activo=True).values_list("estudiante_id", flat=True)
    )
    total_general = Sena.objects.filter(estado=True, leccion__estado=True, leccion__modulo__estado=True).count()
    limite = timezone.now() - timedelta(days=DIAS_SIN_ACTIVIDAD)
    filas = []
    for estudiante in estudiantes:
        datos = practicas.get(estudiante.pk, {})
        total, logradas = total_general, dominadas.get(estudiante.pk, 0)
        if estudiante.pk in con_asignacion:
            alcance = alcance_contenido(estudiante)
            propias = set(
                ProgresoSena.objects.filter(usuario=estudiante, dominada=True).values_list("sena_id", flat=True)
            )
            total, logradas = len(alcance.senas), len(alcance.senas & propias)
        ultima = datos.get("ultima")
        intentos = datos.get("intentos", 0)
        filas.append({
            "estudiante": estudiante,
            "intentos": intentos,
            "tasa": round(datos.get("aciertos", 0) / intentos * 100, 1) if intentos else 0.0,
            "ultima": timezone.localtime(ultima) if ultima else None,
            "dominadas": logradas,
            "total": total,
            "porcentaje": round(logradas / total * 100) if total else 0,
            "con_contenido": estudiante.pk in con_asignacion,
            "sin_actividad": ultima is None or ultima < limite,
        })
    return filas


def resumen_profesores() -> list[dict]:
    """Profesores activos con la cantidad de estudiantes y los que están sin actividad (administrador)."""
    filas = []
    for profesor in profesores_activos().order_by("apellido", "nombre"):
        avance = avance_estudiantes(profesor)
        filas.append({
            "profesor": profesor,
            "estudiantes": len(avance),
            "sin_actividad": sum(1 for fila in avance if fila["sin_actividad"]),
            "ultimo_acceso": profesor.ultimo_acceso,
        })
    return filas
