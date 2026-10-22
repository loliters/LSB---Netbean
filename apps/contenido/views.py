"""Vistas de navegación del contenido pedagógico."""
from django.http import Http404
from django.shortcuts import render

from apps.core.utils import entero_o_none

from . import services


def mapa_modulos(request):
    """Catálogo de módulos con filtros por dificultad y búsqueda (HU-03)."""
    id_dificultad = entero_o_none(request.GET.get("dificultad"))
    busqueda = request.GET.get("q", "").strip()[:60]
    return render(request, "contenido/mapa_modulos.html", {
        "modulos": services.listar_modulos_con_progreso(request.user, id_dificultad, busqueda),
        "dificultades": services.listar_dificultades(),
        "dificultad_actual": id_dificultad,
        "busqueda": busqueda,
    })


def detalle_modulo(request, id_modulo: int):
    """Lecciones y señas de un módulo (HU-04)."""
    modulo, dominadas = services.detalle_modulo(id_modulo, request.user)
    if modulo is None:
        raise Http404("El módulo no existe o no está disponible.")
    return render(request, "contenido/modulo_detalle.html", {
        "modulo": modulo,
        "dominadas": dominadas,
    })
