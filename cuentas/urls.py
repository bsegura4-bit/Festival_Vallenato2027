from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("ingresar/", views.IngresoView.as_view(), name="login"),
    path("salir/", views.SalidaView.as_view(), name="logout"),
    path("perfil/", views.perfil, name="perfil"),
]
