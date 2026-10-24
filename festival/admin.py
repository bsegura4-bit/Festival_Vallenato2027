from django.contrib import admin, messages
from django.db.models import Count

from .models import Categoria, Edicion, Opcion, Votacion, Voto

admin.site.site_header = "Votaciones Festival Vallenato · Administración"
admin.site.site_title = "Admin Festival Vallenato"
admin.site.index_title = "Gestión de ediciones, categorías, votaciones y opciones"


class CategoriaInline(admin.TabularInline):
    model = Categoria
    extra = 0
    fields = ("nombre", "orden", "activa")
    show_change_link = True


@admin.register(Edicion)
class EdicionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "anio", "numero", "lugar", "fecha_inicio", "fecha_fin", "activa", "total_categorias")
    list_filter = ("activa",)
    list_editable = ("activa",)
    search_fields = ("nombre", "anio")
    inlines = [CategoriaInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_categorias=Count("categorias"))

    @admin.display(description="categorías", ordering="_categorias")
    def total_categorias(self, obj):
        return obj._categorias


class VotacionInline(admin.TabularInline):
    model = Votacion
    extra = 0
    fields = ("titulo", "estado", "fecha_apertura", "fecha_cierre")
    show_change_link = True


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "edicion", "orden", "activa", "total_votaciones")
    list_filter = ("edicion", "activa")
    list_editable = ("orden", "activa")
    search_fields = ("nombre", "descripcion")
    autocomplete_fields = ("edicion",)
    inlines = [VotacionInline]

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("edicion").annotate(_votaciones=Count("votaciones"))

    @admin.display(description="votaciones", ordering="_votaciones")
    def total_votaciones(self, obj):
        return obj._votaciones


class OpcionInline(admin.TabularInline):
    model = Opcion
    extra = 2
    fields = ("nombre", "descripcion", "orden", "activa")


@admin.register(Votacion)
class VotacionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "edicion_anio", "modalidad", "estado", "fecha_apertura", "fecha_cierre", "total_opciones")
    list_filter = ("estado", "modalidad", "categoria__edicion", "categoria")
    search_fields = ("titulo", "descripcion", "categoria__nombre")
    autocomplete_fields = ("categoria",)
    inlines = [OpcionInline]
    actions = ["abrir_votaciones", "cerrar_votaciones"]
    fieldsets = (
        (None, {"fields": ("categoria", "titulo", "descripcion", "modalidad")}),
        ("Estado y periodo", {"fields": ("estado", "fecha_apertura", "fecha_cierre")}),
        ("Reglas (pendientes de validación con la Fundación)", {"fields": ("votos_por_usuario", "publicar_resultados")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("categoria__edicion").annotate(_opciones=Count("opciones"))

    @admin.display(description="edición", ordering="categoria__edicion__anio")
    def edicion_anio(self, obj):
        return obj.categoria.edicion.anio

    @admin.display(description="opciones", ordering="_opciones")
    def total_opciones(self, obj):
        return obj._opciones

    def save_related(self, request, form, formsets, change):
        # RN-02: si no tiene dos opciones activas vuelve a borrador
        super().save_related(request, form, formsets, change)
        votacion = form.instance
        if votacion.estado == Votacion.Estado.ABIERTA and not votacion.puede_abrirse():
            votacion.estado = Votacion.Estado.BORRADOR
            votacion.save(update_fields=["estado"])
            self.message_user(
                request,
                f"«{votacion}» quedó en borrador: necesita al menos dos opciones activas para abrirse (RN-02).",
                messages.WARNING,
            )

    @admin.action(description="Abrir las votaciones seleccionadas")
    def abrir_votaciones(self, request, queryset):
        abiertas, rechazadas = 0, []
        for votacion in queryset:
            if votacion.puede_abrirse():
                votacion.estado = Votacion.Estado.ABIERTA
                votacion.save(update_fields=["estado", "actualizado"])
                abiertas += 1
            else:
                rechazadas.append(str(votacion))
        if abiertas:
            self.message_user(request, f"{abiertas} votación(es) abiertas.", messages.SUCCESS)
        if rechazadas:
            self.message_user(
                request, "No se abrieron (menos de dos opciones): " + ", ".join(rechazadas), messages.WARNING,
            )

    @admin.action(description="Cerrar las votaciones seleccionadas")
    def cerrar_votaciones(self, request, queryset):
        total = queryset.update(estado=Votacion.Estado.CERRADA)
        self.message_user(request, f"{total} votación(es) cerradas.", messages.SUCCESS)


@admin.register(Opcion)
class OpcionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "votacion", "orden", "activa")
    list_filter = ("activa", "votacion__categoria__edicion", "votacion")
    list_editable = ("orden", "activa")
    search_fields = ("nombre", "descripcion", "votacion__titulo")
    autocomplete_fields = ("votacion",)


@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ("votacion", "opcion", "usuario", "fecha")
    list_filter = ("votacion",)
    readonly_fields = ("usuario", "votacion", "opcion", "fecha")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
