from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


class CorreoOUsuarioBackend(ModelBackend):
    # permite entrar con el correo o con el usuario

    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        Usuario = get_user_model()
        usuario = (
            Usuario.objects.filter(email__iexact=username).order_by("pk").first()
            or Usuario.objects.filter(username__iexact=username).first()
        )
        if usuario is None:
            Usuario().set_password(password)
            return None
        if usuario.check_password(password) and self.user_can_authenticate(usuario):
            return usuario
        return None
