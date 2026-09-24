from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Usuario


class LoginForm(forms.Form):
    """Formulario de inicio de sesión con usuario o correo."""
    identificador = forms.CharField(
        label='Usuario o correo',
        max_length=150,
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput,
    )


class RegistroForm(UserCreationForm):
    """Formulario de registro de estudiante (HU-02)."""
    correo = forms.EmailField(required=True)

    class Meta:
        model = Usuario
        fields = ('username', 'correo', 'password1', 'password2')