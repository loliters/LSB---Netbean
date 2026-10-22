"""Vistas de práctica con cámara y predicción de señas (HU-04, HU-05)."""
import logging

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.contenido.models import Sena
from apps.core.utils import leer_json
from apps.progreso.models import ProgresoSena
from apps.usuarios.models import EstadisticasUsuario
from ia.cargador import ModeloNoDisponibleError
from ia.predictor import predecir_desde_base64

logger = logging.getLogger(__name__)


@login_required
def practica(request, id_sena: int):
    """Pantalla de práctica de una seña con la cámara."""
    sena = get_object_or_404(
        Sena.objects.select_related("leccion__modulo", "dificultad"),
        pk=id_sena,
        estado=True,
        leccion__estado=True,
    )
    hermanas = list(
        Sena.objects.filter(leccion=sena.leccion, estado=True)
        .order_by("id_sena")
        .values_list("id_sena", flat=True)
    )
    posicion = hermanas.index(sena.pk)
    estadisticas, _ = EstadisticasUsuario.objects.get_or_create(usuario=request.user)
    dominadas = ProgresoSena.objects.filter(
        usuario=request.user, sena_id__in=hermanas, dominada=True
    ).count()
    return render(request, "reconocimiento/practica.html", {
        "sena": sena,
        "dominadas": dominadas,
        "posicion": posicion + 1,
        "total": len(hermanas),
        "siguiente_id": hermanas[posicion + 1] if posicion + 1 < len(hermanas) else None,
        "estadisticas": estadisticas,
    })


@login_required
def continuar(request):
    """Abre la primera seña aún no dominada; si no hay, el catálogo."""
    dominadas = ProgresoSena.objects.filter(usuario=request.user, dominada=True).values("sena_id")
    pendiente = (
        Sena.objects.filter(estado=True, leccion__estado=True, leccion__modulo__estado=True)
        .exclude(pk__in=dominadas)
        .order_by("leccion__modulo__categoria_id", "leccion__modulo__orden", "leccion__orden", "id_sena")
        .first()
    )
    if pendiente is None:
        return redirect("contenido:mapa_modulos")
    return redirect("reconocimiento:practica", id_sena=pendiente.pk)


@login_required
@require_POST
def predecir(request):
    """Predice la letra de un fotograma Base64. No guarda nada en BD."""
    frame = leer_json(request).get("frame")
    if not frame:
        return JsonResponse({"error": "No se recibió el fotograma."}, status=400)
    try:
        prediccion = predecir_desde_base64(frame)
    except ModeloNoDisponibleError:
        logger.exception("Modelo de IA no disponible")
        return JsonResponse(
            {"error": "El reconocimiento no está disponible en este momento."}, status=503
        )
    return JsonResponse(prediccion.a_dict())