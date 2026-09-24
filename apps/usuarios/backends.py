from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

Usuario = get_user_model()


class CorreoBackend(ModelBackend):
    """Permite autenticar con username o correo."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(Usuario.USERNAME_FIELD)
        if username is None or password is None:
            return None

        try:
            user = Usuario.objects.get(username=username)
        except Usuario.DoesNotExist:
            try:
                user = Usuario.objects.get(correo=username)
            except Usuario.DoesNotExist:
                return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None