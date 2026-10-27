"""Formularios de acceso, registro y recuperación de contraseña."""
import re

from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError

from .models import Usuario

PATRON_CORREO = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.IGNORECASE)
LONGITUD_MINIMA_CONTRASENA = 8
AYUDA_CONTRASENA = "Mínimo 8 caracteres, con letras y números."


def validar_formato_correo(correo: str | None) -> str:
    """Normaliza el correo y verifica su formato."""
    correo = (correo or "").strip().lower()
    if not PATRON_CORREO.match(correo):
        raise ValidationError("Ingresa un correo válido, por ejemplo nombre@correo.com.")
    return correo


def validar_contrasena_segura(contrasena: str) -> None:
    """Exige longitud mínima de 8 y combinación de letras y números."""
    errores = []
    if len(contrasena) < LONGITUD_MINIMA_CONTRASENA:
        errores.append("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", contrasena) or not re.search(r"\d", contrasena):
        errores.append("La contraseña debe contener letras y números.")
    if errores:
        raise ValidationError(errores)


def _atributos(placeholder: str, autocomplete: str) -> dict:
    return {"class": "campo__input", "placeholder": placeholder, "autocomplete": autocomplete}


def _campo_contrasena(etiqueta: str, autocomplete: str, ayuda: str = "") -> forms.CharField:
    return forms.CharField(
        label=etiqueta,
        strip=False,
        help_text=ayuda,
        widget=forms.PasswordInput(attrs=_atributos("••••••••", autocomplete)),
    )


class ConfirmacionContrasenaMixin:
    """Validación compartida para formularios con password1/password2."""

    def clean_password1(self):
        contrasena = self.cleaned_data.get("password1", "")
        validar_contrasena_segura(contrasena)
        return contrasena

    def _validar_confirmacion(self, usuario) -> None:
        contrasena = self.cleaned_data.get("password1")
        confirmacion = self.cleaned_data.get("password2")
        if not contrasena or not confirmacion:
            return
        if contrasena != confirmacion:
            self.add_error("password2", "Las contraseñas no coinciden.")
            return
        try:
            password_validation.validate_password(contrasena, user=usuario)
        except ValidationError as error:
            self.add_error("password1", error)


class LoginForm(forms.Form):
    """Inicio de sesión con correo y contraseña (HU-01)."""

    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs=_atributos("ejemplo@correo.com", "email")),
    )
    password = _campo_contrasena("Contraseña", "current-password")
    recordarme = forms.BooleanField(label="Recordarme", required=False, initial=True)


class RegistroForm(ConfirmacionContrasenaMixin, forms.ModelForm):
    """Registro de estudiante (HU-02). El rol se asigna en el servidor."""

    password1 = _campo_contrasena("Contraseña", "new-password", AYUDA_CONTRASENA)
    password2 = _campo_contrasena("Confirmar contraseña", "new-password")

    class Meta:
        model = Usuario
        fields = ("nombre", "apellido", "correo")
        widgets = {
            "nombre": forms.TextInput(attrs=_atributos("Tu nombre", "given-name")),
            "apellido": forms.TextInput(attrs=_atributos("Tu apellido", "family-name")),
            "correo": forms.EmailInput(attrs=_atributos("ejemplo@correo.com", "email")),
        }
        labels = {"correo": "Correo electrónico"}

    def clean_correo(self):
        correo = validar_formato_correo(self.cleaned_data.get("correo"))
        if Usuario.objects.filter(correo__iexact=correo).exists():
            raise ValidationError("Ya existe una cuenta con este correo.")
        return correo

    def clean(self):
        datos = super().clean()
        candidato = Usuario(
            nombre=datos.get("nombre", ""),
            apellido=datos.get("apellido", ""),
            correo=datos.get("correo", ""),
        )
        self._validar_confirmacion(candidato)
        return datos

    def save(self, commit: bool = True) -> Usuario:
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario


class RecuperarPasswordForm(forms.Form):
    """Solicitud de enlace de recuperación (HU-12)."""

    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs=_atributos("ejemplo@correo.com", "email")),
    )

    def clean_correo(self):
        return validar_formato_correo(self.cleaned_data.get("correo"))


class RestablecerPasswordForm(ConfirmacionContrasenaMixin, forms.Form):
    """Definición de la nueva contraseña (HU-12)."""

    password1 = _campo_contrasena("Nueva contraseña", "new-password", AYUDA_CONTRASENA)
    password2 = _campo_contrasena("Confirmar contraseña", "new-password")

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean(self):
        datos = super().clean()
        self._validar_confirmacion(self.usuario)
        return datos


class CambiarPasswordForm(ConfirmacionContrasenaMixin, forms.Form):
    """Cambio de contraseña desde el perfil (pide la contraseña actual)."""

    actual = _campo_contrasena("Contraseña actual", "current-password")
    password1 = _campo_contrasena("Nueva contraseña", "new-password", AYUDA_CONTRASENA)
    password2 = _campo_contrasena("Confirmar nueva contraseña", "new-password")

    def __init__(self, *args, usuario=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.usuario = usuario

    def clean_actual(self):
        actual = self.cleaned_data.get("actual", "")
        if not self.usuario.check_password(actual):
            raise ValidationError("La contraseña actual no es correcta.")
        return actual

    def clean(self):
        datos = super().clean()
        if datos.get("password1") and datos.get("password1") == datos.get("actual"):
            self.add_error("password1", "La nueva contraseña debe ser distinta de la actual.")
        self._validar_confirmacion(self.usuario)
        return datos


class UsuarioGestionForm(forms.ModelForm):
    """Edición de usuarios desde el panel del administrador (HU-09)."""

    class Meta:
        model = Usuario
        fields = ("nombre", "apellido", "correo", "rol", "estado")
        widgets = {
            "nombre": forms.TextInput(attrs=_atributos("Nombre", "off")),
            "apellido": forms.TextInput(attrs=_atributos("Apellido", "off")),
            "correo": forms.EmailInput(attrs=_atributos("ejemplo@correo.com", "off")),
            "rol": forms.Select(attrs={"class": "campo__input campo__input--select"}),
        }
        labels = {"correo": "Correo electrónico", "estado": "Cuenta activa"}

    def __init__(self, *args, editor=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor = editor

    def clean_correo(self):
        correo = validar_formato_correo(self.cleaned_data.get("correo"))
        repetido = Usuario.objects.filter(correo__iexact=correo).exclude(pk=self.instance.pk)
        if repetido.exists():
            raise ValidationError("Ya existe otra cuenta con este correo.")
        return correo

    def clean(self):
        datos = super().clean()
        es_el_mismo = self.editor is not None and self.instance.pk == self.editor.pk
        if es_el_mismo and "estado" in self.fields and not datos.get("estado", True):
            self.add_error("estado", "No puedes desactivar tu propia cuenta.")
        rol = datos.get("rol")
        if es_el_mismo and rol and rol.nombre_rol.lower() != "administrador":
            self.add_error("rol", "No puedes quitarte el rol de administrador.")
        return datos


class UsuarioCrearForm(ConfirmacionContrasenaMixin, UsuarioGestionForm):
    """Alta de profesores, administradores o estudiantes desde el panel."""

    password1 = _campo_contrasena("Contraseña", "new-password", AYUDA_CONTRASENA)
    password2 = _campo_contrasena("Confirmar contraseña", "new-password")

    class Meta(UsuarioGestionForm.Meta):
        fields = ("nombre", "apellido", "correo", "rol")

    def clean(self):
        datos = super().clean()
        candidato = Usuario(
            nombre=datos.get("nombre", ""),
            apellido=datos.get("apellido", ""),
            correo=datos.get("correo", ""),
        )
        self._validar_confirmacion(candidato)
        return datos

    def save(self, commit: bool = True) -> Usuario:
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        if commit:
            usuario.save()
        return usuario