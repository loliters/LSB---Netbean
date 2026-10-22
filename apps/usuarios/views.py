"""Vistas de autenticación, recuperación de contraseña y paneles por rol."""
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.contenido import services as contenido_services
from apps.contenido.models import Modulo
from apps.core.models import Categoria, Rol
from apps.core.utils import leer_json

from . import services
from .decoradores import rol_requerido
from .forms import (
    LoginForm,
    RecuperarPasswordForm,
    RegistroForm,
    RestablecerPasswordForm,
    validar_formato_correo,
)
from .models import Usuario

BACKEND = "apps.usuarios.backends.CorreoBackend"
MENSAJE_RECUPERACION = (
    "Si el correo está registrado, te enviamos un enlace válido por 30 minutos."
)
PANEL_POR_ROL = {
    "administrador": "usuarios:panel_admin",
    "profesor": "usuarios:panel_profesor",
}


def _redirigir_por_rol(usuario):
    """Redirige al panel que corresponde al rol del usuario."""
    return redirect(PANEL_POR_ROL.get(usuario.nombre_rol, "usuarios:panel_estudiante"))


@login_required
def panel(request):
    """Punto de entrada único al panel según rol."""
    return _redirigir_por_rol(request.user)


def login_view(request):
    """Inicia sesión con correo y contraseña (HU-01)."""
    if request.user.is_authenticated:
        return _redirigir_por_rol(request.user)
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = authenticate(
            request,
            correo=form.cleaned_data["correo"],
            password=form.cleaned_data["password"],
        )
        if usuario is None:
            form.add_error(None, "Correo o contraseña incorrectos.")
        else:
            login(request, usuario, backend=BACKEND)
            if not form.cleaned_data["recordarme"]:
                request.session.set_expiry(0)
            Usuario.objects.filter(pk=usuario.pk).update(ultimo_acceso=timezone.now())
            destino = request.GET.get("next", "")
            if url_has_allowed_host_and_scheme(destino, {request.get_host()}):
                return redirect(destino)
            return _redirigir_por_rol(usuario)
    return render(request, "usuarios/login.html", {"form": form})


@require_POST
def logout_view(request):
    """Cierra la sesión del usuario."""
    logout(request)
    return redirect("usuarios:login")


def registro_view(request):
    """Registra un nuevo estudiante (HU-02)."""
    if request.user.is_authenticated:
        return _redirigir_por_rol(request.user)
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = services.registrar_estudiante(form)
        login(request, usuario, backend=BACKEND)
        messages.success(request, f"Tu cuenta está lista, {usuario.nombre}.")
        return redirect("usuarios:panel_estudiante")
    return render(request, "usuarios/registro.html", {"form": form})


def recuperar_password_view(request):
    """Formulario HTML para solicitar el enlace de recuperación (HU-12)."""
    form = RecuperarPasswordForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        services.solicitar_recuperacion(form.cleaned_data["correo"], request.build_absolute_uri)
        messages.success(request, MENSAJE_RECUPERACION)
        return redirect("usuarios:login")
    return render(request, "usuarios/recuperar_password.html", {"form": form})


@require_POST
def api_recuperar_password(request):
    """Endpoint JSON de recuperación. Responde igual exista o no el correo."""
    try:
        correo = validar_formato_correo(leer_json(request).get("correo"))
    except ValidationError as error:
        return JsonResponse({"ok": False, "error": error.messages[0]}, status=400)
    services.solicitar_recuperacion(correo, request.build_absolute_uri)
    return JsonResponse({"ok": True, "mensaje": MENSAJE_RECUPERACION})


def restablecer_password_view(request, token: str):
    """Permite definir una nueva contraseña con un token vigente (HU-12)."""
    registro = services.obtener_token_vigente(token)
    if registro is None:
        return render(request, "usuarios/restablecer_password.html", {"invalido": True}, status=400)
    form = RestablecerPasswordForm(request.POST or None, usuario=registro.usuario)
    if request.method == "POST" and form.is_valid():
        services.restablecer_contrasena(token, form.cleaned_data["password1"])
        messages.success(request, "Contraseña actualizada. Ya puedes iniciar sesión.")
        return redirect("usuarios:login")
    return render(request, "usuarios/restablecer_password.html", {"form": form})


@rol_requerido("estudiante")
def panel_estudiante(request):
    """Panel del estudiante: XP, racha, nivel y módulos con progreso."""
    contexto = services.resumen_estudiante(request.user)
    modulos = contenido_services.listar_modulos_con_progreso(request.user)
    pendientes = [m for m in modulos if m.porcentaje < 100]
    contexto["modulo_actual"] = max(pendientes, key=lambda m: m.porcentaje, default=None)
    contexto["modulos"] = modulos[:6]
    return render(request, "usuarios/panel_estudiante.html", contexto)


@rol_requerido("profesor")
def panel_profesor(request):
    """Panel del profesor: resumen de contenido."""
    return render(request, "usuarios/panel_profesor.html", {
        "total_categorias": Categoria.objects.filter(activo=True).count(),
        "total_modulos": Modulo.objects.filter(estado=True).count(),
        "total_estudiantes": Usuario.objects.filter(rol__nombre_rol__iexact="estudiante").count(),
    })


@rol_requerido("administrador")
def panel_admin(request):
    """Panel del administrador: métricas globales."""
    usuarios = Usuario.objects.all()
    roles = {r.nombre_rol.lower(): r.pk for r in Rol.objects.all()}
    return render(request, "usuarios/panel_admin.html", {
        "id_rol_estudiante": roles.get("estudiante"),
        "id_rol_profesor": roles.get("profesor"),
        "total_usuarios": usuarios.count(),
        "total_estudiantes": usuarios.filter(rol__nombre_rol__iexact="estudiante").count(),
        "total_profesores": usuarios.filter(rol__nombre_rol__iexact="profesor").count(),
        "total_categorias": Categoria.objects.count(),
        "total_modulos": Modulo.objects.count(),
    })