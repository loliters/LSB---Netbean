"""Formularios de gestión de contenido pedagógico (HU-08)."""
from pathlib import Path

from django import forms
from django.core.exceptions import ValidationError

from apps.core.models import Categoria

from . import services
from .models import Leccion, Modulo, Sena

TAMANO_MAXIMO_IMAGEN = 2 * 1024 * 1024  # manual 1.5 y 1.8
EXTENSIONES_IMAGEN = {".jpg", ".jpeg", ".png", ".webp"}


def _aplicar_clases(formulario: forms.BaseForm) -> None:
    """Asigna las clases visuales de Net Bean a cada widget."""
    for campo in formulario.fields.values():
        widget = campo.widget
        if isinstance(widget, forms.CheckboxInput):
            continue
        if isinstance(widget, forms.Select):
            widget.attrs.setdefault("class", "campo__input campo__input--select")
        elif isinstance(widget, forms.FileInput):
            widget.attrs.setdefault("class", "campo__input campo__input--archivo")
        else:
            widget.attrs.setdefault("class", "campo__input campo__input--sin-icono")
        if isinstance(widget, forms.Textarea):
            widget.attrs.setdefault("rows", 3)


class ModuloForm(forms.ModelForm):
    class Meta:
        model = Modulo
        fields = ("categoria", "dificultad", "nombre", "descripcion", "orden", "xp_recompensa")
        labels = {"xp_recompensa": "XP de recompensa", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].queryset = Categoria.objects.filter(activo=True).order_by("nombre")
        _aplicar_clases(self)

    def clean(self):
        datos = super().clean()
        categoria, orden = datos.get("categoria"), datos.get("orden")
        repetido = Modulo.objects.filter(categoria=categoria, orden=orden).exclude(pk=self.instance.pk)
        if categoria and orden is not None and repetido.exists():
            self.add_error("orden", "Ya existe un módulo con ese orden en la categoría.")
        return datos


class LeccionForm(forms.ModelForm):
    class Meta:
        model = Leccion
        fields = ("nombre", "descripcion", "orden", "xp_recompensa")
        labels = {"xp_recompensa": "XP de recompensa", "descripcion": "Descripción"}
        widgets = {"descripcion": forms.Textarea}

    def __init__(self, *args, modulo: Modulo, **kwargs):
        super().__init__(*args, **kwargs)
        self.modulo = modulo
        _aplicar_clases(self)

    def clean_orden(self):
        orden = self.cleaned_data["orden"]
        repetido = Leccion.objects.filter(modulo=self.modulo, orden=orden).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError("Ya existe una lección con ese orden en el módulo.")
        return orden

    def save(self, commit: bool = True) -> Leccion:
        self.instance.modulo = self.modulo
        return super().save(commit)


class SenaForm(forms.ModelForm):
    imagen = forms.ImageField(
        label="Imagen de referencia",
        required=False,
        help_text="JPG, PNG o WEBP de hasta 2 MB. Obligatoria al crear la seña.",
    )

    class Meta:
        model = Sena
        fields = ("nombre", "tipo_sena", "dificultad", "puntos_minimos")
        labels = {"tipo_sena": "Tipo de seña", "puntos_minimos": "Porcentaje mínimo para aprobar"}
        help_texts = {"nombre": "Debe coincidir con una letra que reconoce el modelo de IA."}

    def __init__(self, *args, leccion: Leccion, **kwargs):
        super().__init__(*args, **kwargs)
        self.leccion = leccion
        _aplicar_clases(self)

    def clean_nombre(self):
        nombre = self.cleaned_data["nombre"].strip().upper()
        etiquetas = services.etiquetas_modelo()
        if etiquetas and nombre not in etiquetas:
            disponibles = ", ".join(sorted(etiquetas))
            raise ValidationError(f"El modelo de IA no reconoce «{nombre}». Usa una de: {disponibles}.")
        repetida = Sena.objects.filter(leccion=self.leccion, nombre__iexact=nombre).exclude(pk=self.instance.pk)
        if repetida.exists():
            raise ValidationError("Esta lección ya tiene una seña con ese nombre.")
        return nombre

    def clean_imagen(self):
        imagen = self.cleaned_data.get("imagen")
        if not imagen:
            return imagen
        if Path(imagen.name).suffix.lower() not in EXTENSIONES_IMAGEN:
            raise ValidationError("Formato no permitido. Usa JPG, PNG o WEBP.")
        if imagen.size > TAMANO_MAXIMO_IMAGEN:
            raise ValidationError("La imagen supera los 2 MB.")
        return imagen

    def clean(self):
        datos = super().clean()
        if not self.instance.pk and not datos.get("imagen") and "imagen" not in self.errors:
            self.add_error("imagen", "Sube la imagen de referencia de la seña.")
        return datos

    def save(self, commit: bool = True) -> Sena:
        sena = super().save(commit=False)
        sena.leccion = self.leccion
        imagen = self.cleaned_data.get("imagen")
        if imagen:
            sena.ruta_imagen = services.guardar_imagen_sena(sena.nombre, imagen)
        if commit:
            sena.save()
        return sena
