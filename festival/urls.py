from django.urls import path

from . import views

app_name = "festival"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("ediciones/", views.EdicionListView.as_view(), name="ediciones"),
    path("ediciones/<int:anio>/", views.edicion_detalle, name="edicion_detalle"),
    path("categorias/", views.categorias, name="categorias"),
    path("categorias/<int:pk>/", views.CategoriaDetailView.as_view(), name="categoria_detalle"),
    path("votaciones/", views.VotacionListView.as_view(), name="votaciones"),
    path("votaciones/<int:pk>/", views.VotacionDetailView.as_view(), name="votacion_detalle"),
]
