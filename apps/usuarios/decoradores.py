from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def rol_requerido(*roles):
    """Restringe una vista a los roles indicados."""
    def decorador(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            if request.user.rol not in roles:
                raise PermissionDenied('No tienes permiso para esta sección.')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorador