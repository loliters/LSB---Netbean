"""Vistas transversales del sistema."""
from django.shortcuts import redirect, render


def inicio(request):
    """Página de inicio pública; los usuarios autenticados van a su panel."""
    if request.user.is_authenticated:
        return redirect("usuarios:panel")
    return render(request, "inicio.html")
