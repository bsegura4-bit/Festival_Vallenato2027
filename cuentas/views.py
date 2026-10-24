from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render

from .forms import IngresoForm, RegistroForm


def registro(request):
    if request.user.is_authenticated:
        return redirect("festival:inicio")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario, backend="cuentas.backends.CorreoOUsuarioBackend")
        messages.success(request, f"¡Bienvenido, {usuario.first_name}! Tu cuenta quedó creada.")
        return redirect("festival:inicio")
    return render(request, "cuentas/registro.html", {"form": form})


class IngresoView(LoginView):
    template_name = "cuentas/login.html"
    authentication_form = IngresoForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, "Sesión iniciada.")
        return super().form_valid(form)


class SalidaView(LogoutView):
    def post(self, request, *args, **kwargs):
        respuesta = super().post(request, *args, **kwargs)
        messages.info(request, "Cerraste sesión.")
        return respuesta


@login_required
def perfil(request):
    return render(request, "cuentas/perfil.html")
