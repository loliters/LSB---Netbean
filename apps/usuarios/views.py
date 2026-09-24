from django.contrib.auth import authenticate, login, logout
from django.shortcuts import redirect, render

from apps.contenido.models import Categoria, Modulo

from .decoradores import rol_requerido
from .forms import LoginForm, RegistroForm
from .models import Usuario


def _redirigir_por_rol(usuario):
    """Devuelve la redirección al panel según el rol."""
    if usuario.es_administrador:
        return redirect('usuarios:panel_admin')
    if usuario.es_profesor:
        return redirect('usuarios:panel_profesor')
    return redirect('usuarios:panel_estudiante')


def login_view(request):
    """Inicia sesión con usuario o correo (HU-01)."""
    if request.user.is_authenticated:
        return _redirigir_por_rol(request.user)

    form = LoginForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = authenticate(
            request,
            username=form.cleaned_data['identificador'],
            password=form.cleaned_data['password'],
        )
        if usuario is not None:
            login(request, usuario)
            return _redirigir_por_rol(usuario)
        form.add_error(None, 'Credenciales inválidas.')

    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    """Cierra la sesión del usuario."""
    logout(request)
    return redirect('usuarios:login')


def registro_view(request):
    """Registra un nuevo estudiante (HU-02)."""
    if request.user.is_authenticated:
        return _redirigir_por_rol(request.user)

    form = RegistroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save(commit=False)
        usuario.rol = Usuario.Rol.ESTUDIANTE
        usuario.save()
        login(request, usuario)
        return redirect('usuarios:panel_estudiante')

    return render(request, 'usuarios/registro.html', {'form': form})


@rol_requerido('ESTUDIANTE')
def panel_estudiante(request):
    """Panel del estudiante: ver módulos disponibles."""
    categorias = (
        Categoria.objects.filter(activo=True)
        .prefetch_related('modulos')
    )
    return render(request, 'usuarios/panel_estudiante.html', {
        'categorias': categorias,
    })


@rol_requerido('PROFESOR')
def panel_profesor(request):
    """Panel del profesor: resumen de contenido."""
    return render(request, 'usuarios/panel_profesor.html', {
        'total_categorias': Categoria.objects.count(),
        'total_modulos': Modulo.objects.count(),
    })


@rol_requerido('ADMINISTRADOR')
def panel_admin(request):
    """Panel del administrador: métricas globales."""
    return render(request, 'usuarios/panel_admin.html', {
        'total_usuarios': Usuario.objects.count(),
        'total_estudiantes': Usuario.objects.filter(rol='ESTUDIANTE').count(),
        'total_profesores': Usuario.objects.filter(rol='PROFESOR').count(),
        'total_categorias': Categoria.objects.count(),
        'total_modulos': Modulo.objects.count(),
    })