"""Gestión de módulos, lecciones y señas (HU-08) para administrador y profesor."""
from django.contrib import messages
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

from apps.usuarios.decoradores import RolRequeridoMixin

from .forms import LeccionForm, ModuloForm, SenaForm
from .models import Leccion, Modulo, Sena


class GestorContenidoMixin(RolRequeridoMixin):
    roles_permitidos = ("administrador", "profesor")


class FormularioContenidoMixin(GestorContenidoMixin):
    """Plantilla, migas y mensaje comunes a los formularios de contenido."""

    template_name = "contenido/gestion_form.html"
    mensaje = "Cambios guardados."

    def migas(self) -> list[tuple[str, str]]:
        return [("Contenido", reverse("contenido:gestion_modulos"))]

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(migas=self.migas(), cancelar_url=self.get_success_url())
        return contexto

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        messages.success(self.request, self.mensaje)
        return respuesta


# ---------- Módulos ----------
class ModuloListView(GestorContenidoMixin, ListView):
    template_name = "contenido/gestion_modulos.html"
    context_object_name = "modulos"

    def get_queryset(self):
        return (
            Modulo.objects.select_related("categoria", "dificultad")
            .annotate(
                total_lecciones=Count("lecciones", distinct=True),
                total_senas=Count("lecciones__senas", distinct=True),
            )
            .order_by("categoria__nombre", "orden")
        )


class ModuloCrearView(FormularioContenidoMixin, CreateView):
    model = Modulo
    form_class = ModuloForm
    extra_context = {"titulo": "Nuevo módulo", "accion": "Crear módulo"}
    mensaje = "Módulo creado."

    def get_success_url(self):
        return reverse("contenido:gestion_modulos")


class ModuloEditarView(FormularioContenidoMixin, UpdateView):
    model = Modulo
    form_class = ModuloForm
    pk_url_kwarg = "id_modulo"
    extra_context = {"titulo": "Editar módulo", "accion": "Guardar cambios"}

    def get_success_url(self):
        return reverse("contenido:gestion_modulos")


# ---------- Lecciones ----------
class LeccionListView(GestorContenidoMixin, ListView):
    template_name = "contenido/gestion_lecciones.html"
    context_object_name = "lecciones"

    def get_queryset(self):
        self.modulo = get_object_or_404(Modulo.objects.select_related("categoria"), pk=self.kwargs["id_modulo"])
        return self.modulo.lecciones.annotate(total_senas=Count("senas")).order_by("orden")

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "modulo": self.modulo}


class LeccionFormMixin(FormularioContenidoMixin):
    model = Leccion
    form_class = LeccionForm

    def modulo_actual(self) -> Modulo:
        raise NotImplementedError

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "modulo": self.modulo_actual()}

    def migas(self):
        modulo = self.modulo_actual()
        return super().migas() + [(modulo.nombre, reverse("contenido:gestion_lecciones", args=[modulo.pk]))]

    def get_success_url(self):
        return reverse("contenido:gestion_lecciones", args=[self.modulo_actual().pk])


class LeccionCrearView(LeccionFormMixin, CreateView):
    extra_context = {"titulo": "Nueva lección", "accion": "Crear lección"}
    mensaje = "Lección creada."

    def modulo_actual(self):
        return get_object_or_404(Modulo, pk=self.kwargs["id_modulo"])


class LeccionEditarView(LeccionFormMixin, UpdateView):
    pk_url_kwarg = "id_leccion"
    extra_context = {"titulo": "Editar lección", "accion": "Guardar cambios"}

    def modulo_actual(self):
        leccion = getattr(self, "object", None) or self.get_object()
        return leccion.modulo


# ---------- Señas ----------
class SenaListView(GestorContenidoMixin, ListView):
    template_name = "contenido/gestion_senas.html"
    context_object_name = "senas"

    def get_queryset(self):
        self.leccion = get_object_or_404(Leccion.objects.select_related("modulo"), pk=self.kwargs["id_leccion"])
        return (
            self.leccion.senas.select_related("tipo_sena", "dificultad")
            .annotate(
                intentos=Count("practica"),
                aciertos=Count("practica", filter=Q(practica__es_correcta=True)),
            )
            .order_by("id_sena")
        )

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "leccion": self.leccion}


class SenaFormMixin(FormularioContenidoMixin):
    model = Sena
    form_class = SenaForm
    extra_context = {"multipart": True}

    def leccion_actual(self) -> Leccion:
        raise NotImplementedError

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "leccion": self.leccion_actual()}

    def migas(self):
        leccion = self.leccion_actual()
        return super().migas() + [
            (leccion.modulo.nombre, reverse("contenido:gestion_lecciones", args=[leccion.modulo_id])),
            (leccion.nombre, reverse("contenido:gestion_senas", args=[leccion.pk])),
        ]

    def get_success_url(self):
        return reverse("contenido:gestion_senas", args=[self.leccion_actual().pk])


class SenaCrearView(SenaFormMixin, CreateView):
    mensaje = "Seña creada."

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "titulo": "Nueva seña", "accion": "Crear seña"}

    def leccion_actual(self):
        return get_object_or_404(Leccion.objects.select_related("modulo"), pk=self.kwargs["id_leccion"])


class SenaEditarView(SenaFormMixin, UpdateView):
    pk_url_kwarg = "id_sena"

    def get_context_data(self, **kwargs):
        return {**super().get_context_data(**kwargs), "titulo": "Editar seña", "accion": "Guardar cambios"}

    def leccion_actual(self):
        sena = getattr(self, "object", None) or self.get_object()
        return sena.leccion


# ---------- Borrado lógico ----------
class CambiarEstadoView(GestorContenidoMixin, View):
    """Activa o desactiva un módulo, lección o seña sin borrarlo."""

    http_method_names = ["post"]
    MODELOS = {"modulo": Modulo, "leccion": Leccion, "sena": Sena}
    NOMBRES = {"modulo": "Módulo", "leccion": "Lección", "sena": "Seña"}

    def post(self, request, tipo: str, pk: int):
        modelo = self.MODELOS.get(tipo)
        if modelo is None:
            return redirect("contenido:gestion_modulos")
        objeto = get_object_or_404(modelo, pk=pk)
        objeto.estado = not objeto.estado
        objeto.save(update_fields=["estado"])
        verbo = "activado" if objeto.estado else "desactivado"
        messages.success(request, f"{self.NOMBRES[tipo]} «{objeto.nombre}» {verbo}.")
        destino = request.POST.get("siguiente", "")
        if url_has_allowed_host_and_scheme(destino, {request.get_host()}):
            return redirect(destino)
        return redirect("contenido:gestion_modulos")
