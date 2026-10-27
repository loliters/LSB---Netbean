"""Vistas de práctica con cámara y predicción de señas (HU-04, HU-05)."""
import logging

from django.conf import settings
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.contenido.models import Sena
from apps.gamificacion.services import umbral_efectivo
from apps.core.utils import leer_json
from apps.progreso.models import ProgresoSena
from apps.usuarios.asignaciones import alcance_contenido
from apps.usuarios.decoradores import rol_requerido
from apps.usuarios.models import EstadisticasUsuario
from ia.cargador import ModeloNoDisponibleError
from ia.predictor import predecir_desde_base64

logger = logging.getLogger(__name__)


@rol_requerido("estudiante")
def practica(request, id_sena: int):
    """Pantalla de práctica de una seña con la cámara."""
    sena = get_object_or_404(
        Sena.objects.select_related("leccion__modulo", "dificultad"),
        pk=id_sena,
        estado=True,
        leccion__estado=True,
        leccion__modulo__estado=True,
    )
    alcance = alcance_contenido(request.user)
    if alcance is not None and sena.pk not in alcance.senas:
        raise Http404("Esta seña no está asignada a tu cuenta.")
    visibles = Sena.objects.filter(leccion=sena.leccion, estado=True)
    if alcance is not None:
        visibles = visibles.filter(pk__in=alcance.senas)
    hermanas = list(visibles.order_by("id_sena").values_list("id_sena", flat=True))
    posicion = hermanas.index(sena.pk)
    estadisticas, _ = EstadisticasUsuario.objects.get_or_create(usuario=request.user)
    ids_dominadas = set(
        ProgresoSena.objects.filter(usuario=request.user, sena_id__in=hermanas, dominada=True)
        .values_list("sena_id", flat=True)
    )
    return render(request, "reconocimiento/practica.html", {
        "sena": sena,
        "dominadas": len(ids_dominadas),
        "ya_dominada": sena.pk in ids_dominadas,
        "posicion": posicion + 1,
        "total": len(hermanas),
        "siguiente_id": hermanas[posicion + 1] if posicion + 1 < len(hermanas) else None,
        "estadisticas": estadisticas,
        "modo": "numero" if sena.nombre.isdigit() else "letra",
        "umbral": umbral_efectivo(sena),
        "segundos_auto": getattr(settings, "PRACTICA_SEGUNDOS_AUTO", 2),
    })


@rol_requerido("estudiante")
def continuar(request):
    """Abre la primera seña aún no dominada; si no hay, el catálogo."""
    dominadas = ProgresoSena.objects.filter(usuario=request.user, dominada=True).values("sena_id")
    candidatas = Sena.objects.filter(estado=True, leccion__estado=True, leccion__modulo__estado=True)
    alcance = alcance_contenido(request.user)
    if alcance is not None:
        candidatas = candidatas.filter(pk__in=alcance.senas)
    pendiente = (
        candidatas
        .exclude(pk__in=dominadas)
        .order_by("leccion__modulo__categoria_id", "leccion__modulo__orden", "leccion__orden", "id_sena")
        .first()
    )
    if pendiente is None:
        return redirect("contenido:mapa_modulos")
    return redirect("reconocimiento:practica", id_sena=pendiente.pk)


@rol_requerido("estudiante")
@require_POST
def predecir(request):
    """Predice la letra de un fotograma Base64. No guarda nada en BD."""
    datos = leer_json(request)
    frame = datos.get("frame")
    if not frame:
        return JsonResponse({"error": "No se recibió el fotograma."}, status=400)
    try:
        prediccion = predecir_desde_base64(frame, modo=datos.get("modo", "letra"))
    except ModeloNoDisponibleError:
        logger.exception("Modelo de IA no disponible")
        return JsonResponse(
            {"error": "El reconocimiento no está disponible en este momento."}, status=503
        )
    return JsonResponse(prediccion.a_dict())
