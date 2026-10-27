"""Endpoints de gamificación: evaluar y registrar intento (HU-05, HU-06, HU-07)."""
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET, require_POST

from apps.contenido.models import Leccion, Sena
from apps.core.utils import entero_o_none, leer_json
from apps.usuarios.asignaciones import puede_ver_sena
from apps.usuarios.decoradores import rol_requerido
from apps.usuarios.models import EstadisticasUsuario
from ia.cargador import ModeloNoDisponibleError
from ia.predictor import predecir_desde_base64

from . import services

logger = logging.getLogger(__name__)


@rol_requerido("estudiante")
@require_POST
def evaluar(request):
    """Predice en el servidor y, si hay mano, guarda el intento (+30 XP si acierta)."""
    datos = leer_json(request)
    id_leccion = entero_o_none(datos.get("id_leccion"))
    if id_leccion is None or not Leccion.objects.filter(pk=id_leccion, estado=True).exists():
        return JsonResponse({"error": "La lección indicada no existe."}, status=404)
    sena = Sena.objects.filter(
        pk=entero_o_none(datos.get("id_sena")), leccion_id=id_leccion, estado=True
    ).first()
    if sena is None:
        return JsonResponse({"error": "La seña no pertenece a esta lección."}, status=404)
    if not puede_ver_sena(request.user, sena):
        return JsonResponse({"error": "Esta seña no está asignada a tu cuenta."}, status=404)
    if not datos.get("frame"):
        return JsonResponse({"error": "No se recibió el fotograma."}, status=400)
    try:
        modo = "numero" if sena.nombre.isdigit() else "letra"
        prediccion = predecir_desde_base64(datos["frame"], modo=modo)
    except ModeloNoDisponibleError:
        logger.exception("Modelo de IA no disponible")
        return JsonResponse({"error": "El reconocimiento no está disponible."}, status=503)
    if not prediccion.mano_detectada:
        return JsonResponse({**prediccion.a_dict(), "registrado": False})
    resultado = services.registrar_intento(
        usuario=request.user,
        sena=sena,
        letra_predicha=prediccion.letra,
        confianza=prediccion.confianza,
    )
    return JsonResponse({**prediccion.a_dict(), **resultado, "registrado": True})


@rol_requerido("estudiante")
@require_GET
def progreso(request):
    """XP total, racha y prácticas del estudiante (HU-06)."""
    estadisticas, _ = EstadisticasUsuario.objects.get_or_create(usuario=request.user)
    return JsonResponse({
        "xp_total": estadisticas.xp_total,
        "racha_dias": estadisticas.racha_dias,
        "total_practicas": estadisticas.total_practicas,
    })


@rol_requerido("estudiante")
def logros(request):
    """Pantalla «Mis logros» con insignias obtenidas y avance (HU-11)."""
    items = services.progreso_logros(request.user)
    obtenidas = [item for item in items if item["obtenido"]]
    pendientes = [item for item in items if not item["obtenido"]]
    return render(request, "gamificacion/logros.html", {
        "items": items,
        "obtenidas": obtenidas,
        "pendientes": pendientes,
        "obtenidos": len(obtenidas),
        "porcentaje": round(len(obtenidas) / len(items) * 100) if items else 0,
        "xp_logros": sum(item["logro"].xp_bonus for item in obtenidas),
    })
