"""Vistas del profesor (HU-13) y de la asignación de profesores por el administrador.

Profesor: ve la lista de estudiantes, se los asigna, y les asigna módulos, lecciones o señas.
Administrador: lista a los profesores y decide qué estudiantes monitorea cada uno.
Los permisos se validan en el servidor con rol_requerido; nunca solo ocultando botones.
"""
from django.contrib import messages
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.progreso.models import Practica

from . import asignaciones
from .decoradores import rol_requerido
from .forms_asignacion import AsignarContenidoForm
from .models import AsignacionContenido, AsignacionProfesor

LIMITE_LISTA = 300


def _ids(valores) -> list[int]:
    return [int(v) for v in valores if str(v).isdigit()]


def _volver(request, por_defecto: str, *args):
    destino = request.POST.get("siguiente", "")
    if destino and url_has_allowed_host_and_scheme(destino, {request.get_host()}):
        return redirect(destino)
    return redirect(por_defecto, *args)


def _ultima_practica(ids: list[int]) -> dict[int, object]:
    filas = Practica.objects.filter(usuario_id__in=ids).values_list("usuario_id").annotate(ultima=Max("fecha_practica"))
    return {usuario: timezone.localtime(ultima) for usuario, ultima in filas}


# ------------------------------------------------------------------ profesor
@rol_requerido("profesor")
def estudiantes(request):
    """Lista de estudiantes del sistema; el profesor se asigna o libera a los que elija."""
    if request.method == "POST":
        ids = _ids(request.POST.getlist("estudiantes"))
        accion = request.POST.get("accion")
        if not ids:
            messages.warning(request, "Marca al menos un estudiante.")
        elif accion == "asignar":
            nuevas = asignaciones.asignar_estudiantes(request.user, ids)
            messages.success(request, f"Ahora monitoreas a {nuevas} estudiante{'s' if nuevas != 1 else ''} más.")
        elif accion == "quitar":
            quitadas = asignaciones.quitar_estudiantes(request.user, ids)
            messages.success(request, f"Dejaste de monitorear a {quitadas} estudiante{'s' if quitadas != 1 else ''}.")
        return _volver(request, "usuarios:profesor_estudiantes")

    todos = list(asignaciones.estudiantes_activos().order_by("apellido", "nombre")[:LIMITE_LISTA])
    ids = [e.pk for e in todos]
    mios = set(asignaciones.ids_de_mis_estudiantes(request.user))
    otros: dict[int, list[str]] = {}
    for asignacion in (
        AsignacionProfesor.objects.filter(estudiante_id__in=ids, activo=True)
        .exclude(profesor=request.user).select_related("profesor")
    ):
        otros.setdefault(asignacion.estudiante_id, []).append(asignacion.profesor.nombre_completo)
    ultimas = _ultima_practica(ids)
    filas = [{
        "estudiante": e,
        "relacion": "mio" if e.pk in mios else ("otro" if e.pk in otros else "libre"),
        "otros": ", ".join(otros.get(e.pk, [])),
        "ultima": ultimas.get(e.pk),
    } for e in todos]
    return render(request, "usuarios/profesor_estudiantes.html", {
        "filas": filas,
        "total_mios": len(mios),
        "url_actual": request.get_full_path(),
    })


@rol_requerido("profesor")
def contenido(request):
    """El profesor decide qué módulos, lecciones o señas ve cada uno de sus estudiantes."""
    form = AsignarContenidoForm(request.POST or None, profesor=request.user)
    if request.method == "POST" and form.is_valid():
        tipo, id_objetivo = form.cleaned_data["objetivo"]
        ids = [e.pk for e in form.cleaned_data["estudiantes"]]
        try:
            nuevas = asignaciones.asignar_contenido(request.user, ids, tipo, id_objetivo)
        except ValueError as error:
            form.add_error("objetivo", str(error))
        else:
            if nuevas:
                messages.success(request, f"Contenido asignado a {nuevas} estudiante{'s' if nuevas != 1 else ''}.")
            else:
                messages.info(request, "Esos estudiantes ya tenían asignado ese contenido.")
            return redirect("usuarios:profesor_contenido")
    return render(request, "usuarios/profesor_contenido.html", {
        "form": form,
        "asignaciones": asignaciones.contenido_asignado_por(request.user),
        "total_estudiantes": asignaciones.mis_estudiantes(request.user).count(),
    })


@rol_requerido("profesor")
@require_POST
def quitar_contenido(request, id_asignacion: int):
    """Quita una asignación de contenido hecha por este profesor."""
    if asignaciones.quitar_contenido(request.user, id_asignacion):
        messages.success(request, "Asignación quitada. El estudiante vuelve a ver el resto del contenido según sus demás asignaciones.")
    else:
        messages.warning(request, "No se encontró esa asignación.")
    return redirect("usuarios:profesor_contenido")


# ------------------------------------------------------------ administrador
@rol_requerido("administrador")
def profesores(request):
    """Profesores activos, con cuántos estudiantes monitorea cada uno."""
    return render(request, "usuarios/gestion_profesores.html", {
        "filas": asignaciones.resumen_profesores(),
        "total_estudiantes": asignaciones.estudiantes_activos().count(),
    })


@rol_requerido("administrador")
def profesor_detalle(request, id_profesor: int):
    """El administrador marca qué estudiantes monitorea un profesor."""
    profesor = get_object_or_404(asignaciones.profesores_activos(), pk=id_profesor)
    if request.method == "POST":
        seleccion = _ids(request.POST.getlist("estudiantes"))
        validos = set(asignaciones.estudiantes_activos().filter(pk__in=seleccion).values_list("pk", flat=True))
        agregados, quitados = asignaciones.sincronizar_estudiantes(profesor, validos, request.user)
        messages.success(
            request,
            f"{profesor.nombre_completo}: {agregados} estudiante{'s' if agregados != 1 else ''} agregado{'s' if agregados != 1 else ''} "
            f"y {quitados} quitado{'s' if quitados != 1 else ''}.",
        )
        return redirect("usuarios:gestion_profesor_detalle", id_profesor=profesor.pk)

    todos = list(asignaciones.estudiantes_activos().order_by("apellido", "nombre")[:LIMITE_LISTA])
    asignados = set(asignaciones.ids_de_mis_estudiantes(profesor))
    ultimas = _ultima_practica([e.pk for e in todos])
    filas = [{"estudiante": e, "asignado": e.pk in asignados, "ultima": ultimas.get(e.pk)} for e in todos]
    return render(request, "usuarios/gestion_profesor_detalle.html", {
        "profesor": profesor,
        "filas": filas,
        "total_asignados": len(asignados),
        "contenidos": AsignacionContenido.objects.filter(profesor=profesor, activo=True).count(),
    })
