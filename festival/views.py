from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import DetailView, ListView

from .models import Categoria, Edicion, Opcion, Votacion, Voto
from .votos import VotoRechazado, registrar_voto, validar_opcion, voto_en_categoria


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

    def get_context_data(self, **kwargs):
        contexto = super().get_context_data(**kwargs)
        contexto["voto_previo"] = voto_en_categoria(self.request.user, self.object.categoria)
        return contexto


@login_required
@require_POST
def votar(request, pk):
    """Paso 1: muestra la confirmación. Paso 2 (confirmar=1): registra el voto."""
    votacion = get_object_or_404(Votacion.objects.publicas().select_related("categoria__edicion"), pk=pk)
    opcion_id = request.POST.get("opcion")

    if request.POST.get("confirmar") != "1":
        try:
            if not votacion.acepta_votos:
                raise VotoRechazado("Esta votación no está habilitada para recibir votos.")
            previo = voto_en_categoria(request.user, votacion.categoria)
            if previo:
                raise VotoRechazado(f"Ya votaste en la categoría {votacion.categoria.nombre}.")
            opcion = validar_opcion(votacion, opcion_id)
        except VotoRechazado as error:
            messages.error(request, str(error))
            return redirect(votacion)
        return render(request, "festival/confirmar_voto.html", {"votacion": votacion, "opcion": opcion})

    try:
        voto = registrar_voto(request.user, votacion.pk, opcion_id)
    except VotoRechazado as error:
        messages.error(request, str(error))
        return redirect(votacion)
    messages.success(
        request, f"¡Voto registrado! Elegiste {voto.opcion} en la categoría {voto.categoria.nombre}.",
    )
    return redirect("festival:mis_votos")


@login_required
def mis_votos(request):
    edicion = Edicion.objects.filter(activa=True).first()
    votos = request.user.votos.select_related("edicion", "categoria", "votacion", "opcion")
    votadas = set(votos.values_list("categoria_id", flat=True))
    pendientes = []
    if edicion:
        abiertas = Votacion.objects.publicas().filter(
            categoria__edicion=edicion, estado=Votacion.Estado.ABIERTA,
        ).select_related("categoria")
        vistas = set()
        for v in abiertas.order_by("categoria__orden", "titulo"):
            if v.acepta_votos and v.categoria_id not in votadas and v.categoria_id not in vistas:
                vistas.add(v.categoria_id)
                pendientes.append(v)
    return render(request, "festival/mis_votos.html", {
        "votos": votos, "pendientes": pendientes, "edicion": edicion,
    })


@staff_member_required
def reporte_votos(request):
    """Consulta administrativa: votos por votación y opción, leídos de MySQL."""
    ediciones = Edicion.objects.all()
    anio = request.GET.get("edicion")
    edicion = ediciones.filter(anio=anio).first() if anio and anio.isdigit() else ediciones.first()
    votaciones = []
    if edicion:
        consulta = (
            Votacion.objects.filter(categoria__edicion=edicion)
            .exclude(estado=Votacion.Estado.BORRADOR)
            .select_related("categoria")
            .annotate(total=Count("votos"))
            .prefetch_related(Prefetch(
                "opciones", queryset=Opcion.objects.annotate(total=Count("votos")).order_by("-total", "orden"),
            ))
            .order_by("categoria__orden", "titulo")
        )
        votaciones = list(consulta)
    ultimos = Voto.objects.filter(edicion=edicion).select_related("usuario", "categoria", "opcion")[:20]
    return render(request, "festival/reporte_votos.html", {
        "edicion": edicion, "ediciones": ediciones, "votaciones": votaciones, "ultimos": ultimos,
        "total_votos": Voto.objects.filter(edicion=edicion).count(),
        "total_votantes": Voto.objects.filter(edicion=edicion).values("usuario").distinct().count(),
    })


@require_GET
def api_categorias(request):
    """GET /api/categorias/ — categorías con sus votaciones y opciones en JSON."""
    ediciones = Edicion.objects.filter(activa=True)
    anio = request.GET.get("edicion")
    edicion = ediciones.filter(anio=anio).first() if anio and anio.isdigit() else ediciones.first()
    if edicion is None:
        return JsonResponse({"error": "No hay una edición publicada con ese año."}, status=404)

    votaciones = Votacion.objects.publicas().prefetch_related(
        Prefetch("opciones", queryset=Opcion.objects.filter(activa=True)),
    )
    categorias = edicion.categorias.filter(activa=True).prefetch_related(
        Prefetch("votaciones", queryset=votaciones, to_attr="votaciones_publicas"),
    ).order_by("orden", "nombre")

    datos = {
        "edicion": {"anio": edicion.anio, "nombre": edicion.nombre, "lugar": edicion.lugar},
        "total_categorias": len(categorias),
        "categorias": [
            {
                "id": c.pk,
                "nombre": c.nombre,
                "descripcion": c.descripcion,
                "votaciones": [
                    {
                        "id": v.pk,
                        "titulo": v.titulo,
                        "estado": v.estado,
                        "acepta_votos": v.acepta_votos,
                        "cierre": timezone.localtime(v.fecha_cierre).isoformat() if v.fecha_cierre else None,
                        "opciones": [
                            {"id": o.pk, "nombre": o.nombre, "descripcion": o.descripcion}
                            for o in v.opciones.all()
                        ],
                    }
                    for v in c.votaciones_publicas
                ],
            }
            for c in categorias
        ],
    }
    return JsonResponse(
        datos, content_type="application/json; charset=utf-8",
        json_dumps_params={"ensure_ascii": False, "indent": 2},
    )
