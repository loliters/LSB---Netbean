"""Gestión de usuarios para el administrador (HU-09): listar, crear, editar y borrado lógico."""
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.core.models import Rol

from .forms import UsuarioCrearForm, UsuarioGestionForm
from .models import EstadisticasUsuario, Usuario

FILTROS_ESTADO = {"activos": True, "inactivos": False}


class SoloAdministradorMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Permite el acceso solo al rol Administrador (manual, sección 1.8)."""

    def test_func(self) -> bool:
        return self.request.user.nombre_rol == "administrador"

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return redirect_to_login(self.request.get_full_path())
        raise PermissionDenied


class UsuarioListView(SoloAdministradorMixin, ListView):
    """Lista de usuarios con búsqueda y filtros por rol y estado."""

    template_name = "usuarios/gestion_usuarios.html"
    context_object_name = "usuarios"
    paginate_by = 15

    def get_queryset(self):
        consulta = Usuario.objects.select_related("rol", "estadisticasusuario").order_by(
            "-estado", "apellido", "nombre"
        )
        busqueda = self.request.GET.get("q", "").strip()
        if busqueda:
            consulta = consulta.filter(
                Q(nombre__icontains=busqueda) | Q(apellido__icontains=busqueda) | Q(correo__icontains=busqueda)
            )
        rol = self.request.GET.get("rol", "")
        if rol.isdigit():
            consulta = consulta.filter(rol_id=int(rol))
        estado = self.request.GET.get("estado", "activos")
        if estado in FILTROS_ESTADO:
            consulta = consulta.filter(estado=FILTROS_ESTADO[estado])
        return consulta

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        parametros = self.request.GET.copy()
        parametros.pop("page", None)
        contexto.update({
            "roles": Rol.objects.order_by("nombre_rol"),
            "busqueda": self.request.GET.get("q", ""),
            "rol_actual": self.request.GET.get("rol", ""),
            "estado_actual": self.request.GET.get("estado", "activos"),
            "parametros": parametros.urlencode(),
            "url_actual": self.request.get_full_path(),
        })
        return contexto


class UsuarioCrearView(SoloAdministradorMixin, CreateView):
    """Alta de un usuario con el rol elegido."""

    form_class = UsuarioCrearForm
    template_name = "usuarios/gestion_usuario_form.html"
    success_url = reverse_lazy("usuarios:gestion_usuarios")
    extra_context = {"titulo": "Nuevo usuario", "accion": "Crear usuario"}

    @transaction.atomic
    def form_valid(self, form):
        respuesta = super().form_valid(form)
        EstadisticasUsuario.objects.get_or_create(usuario=self.object)
        messages.success(self.request, f"Usuario {self.object.nombre_completo} creado.")
        return respuesta


class UsuarioEditarView(SoloAdministradorMixin, UpdateView):
    """Edición de datos, rol y estado de un usuario."""

    model = Usuario
    form_class = UsuarioGestionForm
    pk_url_kwarg = "id_usuario"
    template_name = "usuarios/gestion_usuario_form.html"
    success_url = reverse_lazy("usuarios:gestion_usuarios")
    extra_context = {"titulo": "Editar usuario", "accion": "Guardar cambios"}

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "editor": self.request.user}

    def form_valid(self, form):
        messages.success(self.request, f"Cambios guardados para {form.instance.nombre_completo}.")
        return super().form_valid(form)


class UsuarioCambiarEstadoView(SoloAdministradorMixin, View):
    """Borrado lógico: desactiva o reactiva la cuenta (estado = False/True)."""

    http_method_names = ["post"]

    def post(self, request, id_usuario: int):
        usuario = get_object_or_404(Usuario, pk=id_usuario)
        if usuario.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propia cuenta.")
        else:
            usuario.estado = not usuario.estado
            usuario.save(update_fields=["estado"])
            verbo = "reactivada" if usuario.estado else "desactivada"
            messages.success(request, f"Cuenta de {usuario.nombre_completo} {verbo}.")
        destino = request.POST.get("siguiente", "")
        if url_has_allowed_host_and_scheme(destino, {request.get_host()}):
            return redirect(destino)
        return redirect(reverse("usuarios:gestion_usuarios"))