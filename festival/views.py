from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, render
from django.views.generic import DetailView, ListView

from .models import Categoria, Edicion, Opcion, Votacion


def _categorias_con_conteo(edicion):
    return (
        edicion.categorias.filter(activa=True)
        .annotate(total_votaciones=Count("votaciones", filter=~Q(votaciones__estado=Votacion.Estado.BORRADOR)))
        .order_by("orden", "nombre")
    )


def inicio(request):
    edicion = Edicion.objects.filter(activa=True).first()
    contexto = {"edicion": edicion}
    if edicion:
        votaciones = Votacion.objects.publicas().filter(categoria__edicion=edicion)
        contexto.update(
            categorias=_categorias_con_conteo(edicion)[:6],
            abiertas=votaciones.filter(estado=Votacion.Estado.ABIERTA).select_related("categoria")[:4],
            total_categorias=edicion.categorias.filter(activa=True).count(),
            total_votaciones=votaciones.count(),
            total_abiertas=votaciones.filter(estado=Votacion.Estado.ABIERTA).count(),
        )
    return render(request, "festival/inicio.html", contexto)


class EdicionListView(ListView):
    template_name = "festival/ediciones.html"
    context_object_name = "ediciones"

    def get_queryset(self):
        return Edicion.objects.filter(activa=True).annotate(
            total_categorias=Count("categorias", filter=Q(categorias__activa=True), distinct=True),
        )


def edicion_detalle(request, anio):
    edicion = get_object_or_404(Edicion, anio=anio, activa=True)
    return render(request, "festival/categorias.html", {
        "edicion": edicion,
        "categorias": _categorias_con_conteo(edicion),
    })


def categorias(request):
    ediciones = Edicion.objects.filter(activa=True)
    anio = request.GET.get("edicion")
    edicion = get_object_or_404(ediciones, anio=anio) if anio and anio.isdigit() else ediciones.first()
    return render(request, "festival/categorias.html", {
        "edicion": edicion,
        "ediciones": ediciones,
        "categorias": _categorias_con_conteo(edicion) if edicion else [],
    })


class CategoriaDetailView(DetailView):
    template_name = "festival/categoria_detalle.html"
    context_object_name = "categoria"

    def get_queryset(self):
        return Categoria.objects.filter(activa=True, edicion__activa=True).select_related("edicion")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["votaciones"] = (
            Votacion.objects.publicas().filter(categoria=self.object)
            .annotate(total_opciones=Count("opciones", filter=Q(opciones__activa=True)))
            .order_by("estado", "titulo")
        )
        return contexto


class VotacionListView(ListView):
    template_name = "festival/votaciones.html"
    context_object_name = "votaciones"

    def get_queryset(self):
        consulta = (
            Votacion.objects.publicas()
            .select_related("categoria__edicion")
            .annotate(total_opciones=Count("opciones", filter=Q(opciones__activa=True)))
        )
        self.estado = self.request.GET.get("estado", "")
        if self.estado in (Votacion.Estado.ABIERTA, Votacion.Estado.CERRADA):
            consulta = consulta.filter(estado=self.estado)
        self.edicion = Edicion.objects.filter(activa=True).first()
        anio = self.request.GET.get("edicion")
        if anio and anio.isdigit():
            self.edicion = Edicion.objects.filter(activa=True, anio=anio).first()
        if self.edicion:
            consulta = consulta.filter(categoria__edicion=self.edicion)
        return consulta.order_by("estado", "categoria__orden", "titulo")

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto.update(estado=self.estado, edicion=self.edicion, ediciones=Edicion.objects.filter(activa=True))
        return contexto


class VotacionDetailView(DetailView):
    template_name = "festival/votacion_detalle.html"
    context_object_name = "votacion"

    def get_queryset(self):
        return Votacion.objects.publicas().select_related("categoria__edicion").prefetch_related(
            Prefetch("opciones", queryset=Opcion.objects.filter(activa=True), to_attr="opciones_activas"),
        )
