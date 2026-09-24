from django.shortcuts import render

from . import services


def mapa_modulos(request):
    """Muestra el mapa de categorías y módulos activos (HU-03)."""
    categorias = services.listar_modulos_activos()
    return render(
        request,
        'contenido/mapa_modulos.html',
        {'categorias': categorias},
    )