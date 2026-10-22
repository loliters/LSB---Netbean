"""Backend de autenticación por correo electrónico."""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

Usuario = get_user_model()


class CorreoBackend(ModelBackend):
    """Autentica con el campo ``correo`` (sin distinguir mayúsculas)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        correo = kwargs.get("correo") or username
        if not correo or password is None:
            return None
        usuario = Usuario.objects.filter(correo__iexact=correo.strip()).first()
        if usuario is None:
            Usuario().set_password(password)  # tiempo constante ante correos inexistentes
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None

    def get_user(self, user_id):
        """Cierra la sesión de cuentas desactivadas (borrado lógico)."""
        usuario = Usuario.objects.select_related("rol").filter(pk=user_id).first()
        return usuario if usuario and self.user_can_authenticate(usuario) else None