from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

Usuario = get_user_model()


class CorreoBackend(ModelBackend):
    """Permite autenticar usando el campo 'correo'."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        # Tomamos el valor si viene como 'correo' (desde views.py) o como 'username' (por compatibilidad)
        identificador = kwargs.get('correo') or username
        
        if identificador is None or password is None:
            return None

        try:
            # ¡CORRECCIÓN! Buscamos directamente por el campo 'correo'
            user = Usuario.objects.get(correo=identificador)
        except Usuario.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        
        return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None