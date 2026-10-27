"""Filtros del reporte de progreso (HU-10, HU-13).

El administrador puede mirar a todos los estudiantes. El profesor solo a los suyos:
el queryset del campo «estudiante» y el alcance de los filtros se limitan en el servidor,
incluso cuando el formulario llega inválido.
"""
from datetime import timedelta

from django import forms
from django.utils import timezone

from apps.contenido.models import Modulo
from apps.usuarios import asignaciones
from apps.usuarios.models import Usuario

from .services import FiltrosReporte

DIAS_POR_DEFECTO = 30
MAXIMO_DIAS = 366


class FiltroReporteForm(forms.Form):
    desde = forms.DateField(label="Desde", widget=forms.DateInput(attrs={"type": "date", "class": "selector"}))
    hasta = forms.DateField(label="Hasta", widget=forms.DateInput(attrs={"type": "date", "class": "selector"}))
    modulo = forms.ModelChoiceField(
        label="Módulo",
        queryset=Modulo.objects.none(),
        required=False,
        empty_label="Todos los módulos",
        widget=forms.Select(attrs={"class": "selector"}),
    )
    estudiante = forms.ModelChoiceField(
        label="Estudiante",
        queryset=Usuario.objects.none(),
        required=False,
        empty_label="Todos los estudiantes",
        widget=forms.Select(attrs={"class": "selector"}),
    )

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario
        self.es_profesor = usuario is not None and usuario.nombre_rol == "profesor"
        modulos = Modulo.objects.filter(estado=True).order_by("nombre")
        if self.es_profesor:
            estudiantes = asignaciones.mis_estudiantes(usuario)
            asignados = asignaciones.modulos_asignados_por(usuario)
            if asignados:  # el profesor que ya asignó contenido filtra por sus módulos
                modulos = modulos.filter(pk__in=asignados)
            self.fields["estudiante"].empty_label = "Todos mis estudiantes"
        else:
            estudiantes = asignaciones.estudiantes_activos()
        self.fields["modulo"].queryset = modulos
        self.fields["estudiante"].queryset = estudiantes.order_by("apellido", "nombre")
        self.fields["estudiante"].label_from_instance = lambda u: f"{u.nombre_completo} · {u.correo}"

    @staticmethod
    def valores_iniciales() -> dict:
        hoy = timezone.localdate()
        return {"desde": hoy - timedelta(days=DIAS_POR_DEFECTO - 1), "hasta": hoy}

    def clean(self):
        datos = super().clean()
        desde, hasta = datos.get("desde"), datos.get("hasta")
        if desde and hasta:
            if desde > hasta:
                raise forms.ValidationError("La fecha inicial no puede ser posterior a la final.")
            if (hasta - desde).days > MAXIMO_DIAS:
                raise forms.ValidationError("El rango no puede superar un año.")
        return datos

    def _alcance(self) -> tuple | None:
        """Estudiantes que este usuario puede ver: todos (None) o solo los del profesor."""
        if self.es_profesor:
            return tuple(asignaciones.ids_de_mis_estudiantes(self.usuario))
        return None

    def filtros(self) -> FiltrosReporte:
        """Filtros validados, o los últimos 30 días si el formulario no es válido.

        El alcance se aplica siempre: un formulario inválido nunca amplía lo que ve el profesor.
        """
        alcance, solo_mios = self._alcance(), self.es_profesor
        if self.is_bound and self.is_valid():
            datos = self.cleaned_data
            return FiltrosReporte(
                desde=datos["desde"], hasta=datos["hasta"], modulo=datos.get("modulo"),
                estudiante=datos.get("estudiante"), alcance=alcance, solo_mios=solo_mios,
            )
        iniciales = self.valores_iniciales()
        return FiltrosReporte(desde=iniciales["desde"], hasta=iniciales["hasta"], alcance=alcance, solo_mios=solo_mios)
