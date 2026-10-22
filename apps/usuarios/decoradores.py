"""Decoradores de autorización por rol."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles: str):
    """Permite el acceso solo a los roles indicados (sin distinguir mayúsculas)."""
    permitidos = {rol.lower() for rol in roles}

    def decorador(vista):
        @wraps(vista)
        @login_required
        def envoltura(request, *args, **kwargs):
            if request.user.nombre_rol not in permitidos:
                raise PermissionDenied
            return vista(request, *args, **kwargs)

        return envoltura

    return decorador
