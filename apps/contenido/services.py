"""Consultas de contenido pedagógico (HU-03, HU-04)."""
from django.db.models import Count, Prefetch, Q

from apps.core.models import Categoria, Dificultad

from .models import Leccion, Modulo, Sena

ICONOS_POR_PALABRA = {
    "alfabeto": "alphabet-uppercase",
    "abecedario": "alphabet-uppercase",
    "saludo": "hand-thumbs-up",
    "numero": "123",
    "número": "123",
    "familia": "people",
    "profesion": "briefcase",
    "profesión": "briefcase",
    "frase": "chat-quote",
    "color": "palette",
}
ICONO_POR_DEFECTO = "hand-index-thumb"


def icono_para(nombre: str) -> str:
    """Elige un icono de Bootstrap Icons según el nombre del módulo."""
    nombre = nombre.lower()
    for palabra, icono in ICONOS_POR_PALABRA.items():
        if palabra in nombre:
            return icono
    return ICONO_POR_DEFECTO


def listar_modulos_activos():
    """Categorías activas con sus módulos activos en ``modulos_activos``."""
    return Categoria.objects.filter(activo=True).prefetch_related(
        Prefetch("modulos", queryset=Modulo.objects.filter(estado=True), to_attr="modulos_activos")
    )


def listar_dificultades():
    return Dificultad.objects.order_by("nivel")


def listar_modulos_con_progreso(usuario=None, id_dificultad=None, busqueda=""):
    """Módulos activos con conteos y porcentaje de señas dominadas.

    Returns:
        Lista de Modulo con atributos extra: total_lecciones, total_senas,
        porcentaje (0-100) e icono.
    """
    from apps.progreso.models import ProgresoSena

    modulos = (
        Modulo.objects.filter(estado=True, categoria__activo=True)
        .select_related("categoria", "dificultad")
        .annotate(
            total_lecciones=Count("lecciones", filter=Q(lecciones__estado=True), distinct=True),
            total_senas=Count(
                "lecciones__senas",
                filter=Q(lecciones__estado=True, lecciones__senas__estado=True),
                distinct=True,
            ),
        )
    )
    if id_dificultad:
        modulos = modulos.filter(dificultad_id=id_dificultad)
    if busqueda:
        modulos = modulos.filter(Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda))

    dominadas = {}
    if usuario is not None and usuario.is_authenticated:
        dominadas = dict(
            ProgresoSena.objects.filter(usuario=usuario, dominada=True, sena__estado=True)
            .values_list("sena__leccion__modulo")
            .annotate(total=Count("id"))
        )
    resultado = list(modulos)
    for modulo in resultado:
        total = modulo.total_senas or 0
        modulo.porcentaje = round(dominadas.get(modulo.pk, 0) / total * 100) if total else 0
        modulo.icono = icono_para(modulo.nombre)
    return resultado


def detalle_modulo(id_modulo: int, usuario=None):
    """Módulo con lecciones y señas activas, y los IDs de señas dominadas."""
    from apps.progreso.models import ProgresoSena

    modulo = (
        Modulo.objects.select_related("categoria", "dificultad")
        .prefetch_related(
            Prefetch(
                "lecciones",
                queryset=Leccion.objects.filter(estado=True).prefetch_related(
                    Prefetch("senas", queryset=Sena.objects.filter(estado=True).order_by("id_sena"))
                ),
                to_attr="lecciones_activas",
            )
        )
        .filter(pk=id_modulo, estado=True)
        .first()
    )
    dominadas = set()
    if modulo and usuario is not None and usuario.is_authenticated:
        dominadas = set(
            ProgresoSena.objects.filter(
                usuario=usuario, dominada=True, sena__leccion__modulo=modulo
            ).values_list("sena_id", flat=True)
        )
    return modulo, dominadas
