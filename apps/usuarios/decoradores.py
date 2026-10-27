"""Autorización por rol para vistas de función y vistas basadas en clases."""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
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


class RolRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Versión para vistas basadas en clases: define ``roles_permitidos``."""

    roles_permitidos: tuple[str, ...] = ()

    def test_func(self) -> bool:
        return self.request.user.nombre_rol in {r.lower() for r in self.roles_permitidos}

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path())
        raise PermissionDenied
