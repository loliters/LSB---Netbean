from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario


class LoginForm(forms.Form):
    """Formulario de inicio de sesión con usuario o correo."""
    identificador = forms.CharField(
        label='Usuario o correo',
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Usuario o correo'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Contraseña'})
    )


class RegistroForm(UserCreationForm):
    """Formulario de registro de estudiante (HU-02)."""
    correo = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Correo electrónico'})
    )
    nombre = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre'})
    )
    apellido = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Apellido'})
    )

    class Meta:
        model = Usuario
        # ¡Aquí estaba el error! Quitamos 'username' y agregamos los campos reales de tu modelo
        fields = ('correo', 'nombre', 'apellido', 'rol', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Personalizamos los widgets de las contraseñas
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Contraseña'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirmar contraseña'
        })
        # Mejorar el widget del campo 'rol' (ForeignKey)
        if 'rol' in self.fields:
            self.fields['rol'].widget.attrs.update({'class': 'form-control'})