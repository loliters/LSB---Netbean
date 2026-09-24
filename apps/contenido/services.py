from django.db.models import Count, Q

from .models import Categoria


def listar_modulos_activos() -> list[dict]:
    """Devuelve los módulos activos agrupados por categoría."""
    categorias = (
        Categoria.objects.filter(activo=True)
        .prefetch_related('modulos')
        .annotate(
            total_modulos=Count(
                'modulos',
                filter=Q(modulos__activo=True),
            )
        )
        .filter(total_modulos__gt=0)
        .order_by('nombre')
    )

    resultado = []
    for categoria in categorias:
        modulos = [
            {
                'id_modulo': m.id_modulo,
                'nombre': m.nombre,
                'descripcion': m.descripcion,
                'orden': m.orden,
            }
            for m in categoria.modulos.filter(activo=True).order_by('orden')
        ]
        resultado.append(
            {
                'id_categoria': categoria.id_categoria,
                'nombre': categoria.nombre,
                'descripcion': categoria.descripcion,
                'modulos': modulos,
            }
        )
    return resultado