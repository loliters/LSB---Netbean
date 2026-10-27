"""Utilidades compartidas entre aplicaciones."""
import json


def leer_json(request) -> dict:
    """Devuelve el cuerpo de la petición como dict (JSON o formulario)."""
    if request.content_type == "application/json":
        try:
            datos = json.loads(request.body or b"{}")
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {}
        return datos if isinstance(datos, dict) else {}
    return request.POST.dict()


def entero_o_none(valor) -> int | None:
    """Convierte a entero positivo o devuelve None."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return None
    return numero if numero > 0 else None
