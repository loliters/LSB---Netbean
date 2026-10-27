"""Dashboard de estadísticas y exportación del reporte de progreso (HU-10, HU-13).

El administrador ve todos los estudiantes; el profesor solo los suyos. Si el profesor pide
un estudiante que no le pertenece, el servidor responde 403 (no basta con ocultar la opción).
"""
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from apps.usuarios import asignaciones
from apps.usuarios.decoradores import rol_requerido

from . import exportadores, services
from .forms import FiltroReporteForm

ROLES_REPORTE = ("administrador", "profesor")
TIPO_EXCEL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _validar_estudiante_del_profesor(request) -> None:
    """403 si un profesor pide el reporte de un estudiante que no es suyo."""
    pedido = request.GET.get("estudiante", "").strip()
    if pedido and not (pedido.isdigit() and asignaciones.es_estudiante_de(request.user, int(pedido))):
        raise PermissionDenied


def _reporte_desde(request) -> tuple[FiltroReporteForm, dict]:
    if request.user.nombre_rol == "profesor":
        _validar_estudiante_del_profesor(request)
    datos = None
    if request.GET:
        # Un enlace como ?estudiante=5 no trae fechas: se completan para no perder el filtro.
        datos = request.GET.copy()
        iniciales = FiltroReporteForm.valores_iniciales()
        datos.setdefault("desde", iniciales["desde"].isoformat())
        datos.setdefault("hasta", iniciales["hasta"].isoformat())
    form = FiltroReporteForm(datos, usuario=request.user, initial=FiltroReporteForm.valores_iniciales())
    return form, services.construir_reporte(form.filtros())


def _descarga(contenido: bytes, tipo: str, extension: str) -> HttpResponse:
    nombre = f"reporte_netbean_{timezone.localdate():%Y%m%d}.{extension}"
    respuesta = HttpResponse(contenido, content_type=tipo)
    respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
    return respuesta


@rol_requerido(*ROLES_REPORTE)
def dashboard(request):
    form, reporte = _reporte_desde(request)
    return render(request, "reportes/dashboard.html", {
        "form": form,
        "reporte": reporte,
        "graficos": services.datos_graficos(reporte),
        "senas_refuerzo": reporte["por_sena"][:10],
        "ranking": reporte["por_estudiante"][:10],
        "consulta": request.GET.urlencode(),
        "es_profesor": form.es_profesor,
        "sin_estudiantes": form.es_profesor and reporte["resumen"]["estudiantes_registrados"] == 0,
    })


@rol_requerido(*ROLES_REPORTE)
def exportar_excel(request):
    _, reporte = _reporte_desde(request)
    return _descarga(exportadores.generar_excel(reporte), TIPO_EXCEL, "xlsx")


@rol_requerido(*ROLES_REPORTE)
def exportar_pdf(request):
    _, reporte = _reporte_desde(request)
    return _descarga(exportadores.generar_pdf(reporte), "application/pdf", "pdf")
