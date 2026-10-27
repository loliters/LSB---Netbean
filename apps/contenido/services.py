"""Consultas de contenido pedagógico (HU-03, HU-04)."""
from django.db.models import Count, Prefetch, Q

from apps.core.models import Categoria, Dificultad
from apps.usuarios.asignaciones import alcance_contenido

from .models import Leccion, Modulo, Sena

ICONOS_POR_PALABRA = {
    "vocal": "chat-square-text",
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

    Un estudiante con contenido asignado por su profesor solo ve (y cuenta) lo asignado.

    Returns:
        Lista de Modulo con atributos extra: total_lecciones, total_senas,
        porcentaje (0-100) e icono.
    """
    from apps.progreso.models import ProgresoSena

    alcance = alcance_contenido(usuario)
    filtro_lecciones = Q(lecciones__estado=True)
    filtro_senas = Q(lecciones__estado=True, lecciones__senas__estado=True)
    if alcance is not None:
        # Lista no vacía: un «__in» vacío dentro de un Count(filter=...) puede fallar según la versión de Django.
        filtro_lecciones &= Q(lecciones__in=list(alcance.lecciones) or [0])
        filtro_senas &= Q(lecciones__senas__in=list(alcance.senas) or [0])
    modulos = (
        Modulo.objects.filter(estado=True, categoria__activo=True)
        .select_related("categoria", "dificultad")
        .annotate(
            total_lecciones=Count("lecciones", filter=filtro_lecciones, distinct=True),
            total_senas=Count("lecciones__senas", filter=filtro_senas, distinct=True),
        )
    )
    if alcance is not None:
        modulos = modulos.filter(pk__in=alcance.modulos)
    if id_dificultad:
        modulos = modulos.filter(dificultad_id=id_dificultad)
    if busqueda:
        modulos = modulos.filter(Q(nombre__icontains=busqueda) | Q(descripcion__icontains=busqueda))

    dominadas = {}
    if usuario is not None and usuario.is_authenticated:
        propias = ProgresoSena.objects.filter(usuario=usuario, dominada=True, sena__estado=True)
        if alcance is not None:
            propias = propias.filter(sena_id__in=alcance.senas)
        dominadas = dict(propias.values_list("sena__leccion__modulo").annotate(total=Count("id")))
    resultado = list(modulos)
    for modulo in resultado:
        total = modulo.total_senas or 0
        modulo.porcentaje = round(dominadas.get(modulo.pk, 0) / total * 100) if total else 0
        modulo.icono = icono_para(modulo.nombre)
    return resultado


def detalle_modulo(id_modulo: int, usuario=None):
    """Módulo con lecciones y señas activas, y los IDs de señas dominadas.

    Si el estudiante tiene contenido asignado y este módulo no está incluido, devuelve (None, set()).
    """
    from apps.progreso.models import ProgresoSena

    alcance = alcance_contenido(usuario)
    if alcance is not None and id_modulo not in alcance.modulos:
        return None, set()
    lecciones = Leccion.objects.filter(estado=True)
    senas = Sena.objects.filter(estado=True)
    if alcance is not None:
        lecciones = lecciones.filter(pk__in=alcance.lecciones)
        senas = senas.filter(pk__in=alcance.senas)
    modulo = (
        Modulo.objects.select_related("categoria", "dificultad")
        .prefetch_related(
            Prefetch(
                "lecciones",
                queryset=lecciones.prefetch_related(Prefetch("senas", queryset=senas.order_by("id_sena"))),
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


NUMEROS_SOPORTADOS = {"1", "2", "3", "4", "5"}  # se reconocen contando dedos con MediaPipe


def etiquetas_modelo() -> set[str]:
    """Señas que el sistema puede evaluar: letras del modelo CNN y números 1-5."""
    from pathlib import Path

    from django.conf import settings

    ruta = Path(getattr(settings, "RUTA_ETIQUETAS", "") or "")
    if not ruta.is_file():
        return set()
    lineas = ruta.read_text(encoding="utf-8").splitlines()
    return {linea.strip().upper() for linea in lineas if linea.strip().isalpha()} | NUMEROS_SOPORTADOS


def guardar_imagen_sena(nombre_sena: str, archivo) -> str:
    """Guarda la imagen de referencia en media/senas/ y devuelve su ruta relativa."""
    from pathlib import Path

    from django.core.files.storage import default_storage

    extension = Path(archivo.name).suffix.lower()
    ruta = default_storage.save(f"senas/{nombre_sena.lower()}{extension}", archivo)
    return ruta.replace("\\", "/")
