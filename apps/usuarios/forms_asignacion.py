"""Formulario del profesor para asignar contenido a sus estudiantes (HU-13)."""
from django import forms

from apps.contenido.models import Leccion, Modulo, Sena

from . import asignaciones


class AsignarContenidoForm(forms.Form):
    """El profesor elige estudiantes suyos y un módulo, lección o seña.

    El queryset de estudiantes se limita a los del profesor: enviar el ID de otro
    estudiante hace que el formulario sea inválido (no se asigna nada).
    """

    estudiantes = forms.ModelMultipleChoiceField(
        label="Estudiantes",
        queryset=None,
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": "Elige al menos un estudiante.",
            "invalid_choice": "Alguno de los estudiantes elegidos no es tuyo.",
            "invalid_pk_value": "Alguno de los estudiantes elegidos no es válido.",
        },
    )
    objetivo = forms.ChoiceField(
        label="Qué asignar",
        widget=forms.Select(attrs={"class": "campo__input campo__input--select campo__input--sin-icono"}),
        error_messages={"invalid_choice": "El contenido elegido no es válido."},
    )

    def __init__(self, *args, profesor, **kwargs):
        super().__init__(*args, **kwargs)
        self.profesor = profesor
        self.fields["estudiantes"].queryset = asignaciones.mis_estudiantes(profesor).order_by("apellido", "nombre")
        self.fields["estudiantes"].label_from_instance = lambda u: f"{u.nombre_completo} · {u.correo}"
        self.fields["objetivo"].choices = self._opciones()

    @staticmethod
    def _opciones():
        modulos = list(Modulo.objects.filter(estado=True, categoria__activo=True).order_by("categoria__nombre", "orden"))
        lecciones = Leccion.objects.filter(estado=True, modulo__estado=True).select_related("modulo").order_by(
            "modulo__orden", "orden")
        senas = Sena.objects.filter(estado=True, leccion__estado=True, leccion__modulo__estado=True).select_related(
            "leccion__modulo").order_by("leccion__modulo__orden", "leccion__orden", "id_sena")
        return [
            ("", "Elige el contenido…"),
            ("Módulos completos", [(f"m:{m.pk}", m.nombre) for m in modulos]),
            ("Lecciones", [(f"l:{le.pk}", f"{le.nombre} · {le.modulo.nombre}") for le in lecciones]),
            ("Letras y números", [(f"s:{s.pk}", f"{s.nombre} · {s.leccion.modulo.nombre}") for s in senas]),
        ]

    def clean_objetivo(self):
        valor = self.cleaned_data["objetivo"]
        try:
            return asignaciones.decodificar_objetivo(valor)
        except ValueError as error:
            raise forms.ValidationError(str(error)) from None
