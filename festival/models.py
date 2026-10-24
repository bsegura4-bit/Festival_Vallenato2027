from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone


class ModeloConFechas(models.Model):

    creado = models.DateTimeField("creado", auto_now_add=True)
    actualizado = models.DateTimeField("actualizado", auto_now=True)

    class Meta:
        abstract = True


class Edicion(ModeloConFechas):
    nombre = models.CharField("nombre", max_length=150)
    anio = models.PositiveSmallIntegerField("año", unique=True)
    numero = models.PositiveSmallIntegerField("número de edición", null=True, blank=True)
    lugar = models.CharField("lugar", max_length=120, default="Valledupar, Cesar")
    fecha_inicio = models.DateField("fecha de inicio", null=True, blank=True)
    fecha_fin = models.DateField("fecha de fin", null=True, blank=True)
    descripcion = models.TextField("descripción", blank=True)
    activa = models.BooleanField(
        "visible al público", default=True,
        help_text="Solo las ediciones visibles aparecen en el sitio público.",
    )

    class Meta:
        verbose_name = "edición"
        verbose_name_plural = "ediciones"
        ordering = ["-anio"]
        constraints = [
            models.CheckConstraint(
                condition=Q(fecha_fin__isnull=True) | Q(fecha_inicio__isnull=True) | Q(fecha_fin__gte=models.F("fecha_inicio")),
                name="edicion_fechas_validas",
            ),
        ]

    def __str__(self):
        return f"{self.nombre} ({self.anio})"

    def clean(self):
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValidationError({"fecha_fin": "La fecha de fin no puede ser anterior a la de inicio."})

    def get_absolute_url(self):
        return reverse("festival:edicion_detalle", args=[self.anio])


class Categoria(ModeloConFechas):
    edicion = models.ForeignKey(
        Edicion, on_delete=models.PROTECT, related_name="categorias", verbose_name="edición",
    )
    nombre = models.CharField("nombre", max_length=150)
    descripcion = models.TextField("descripción", blank=True)
    orden = models.PositiveSmallIntegerField("orden", default=0)
    activa = models.BooleanField("visible al público", default=True)

    class Meta:
        verbose_name = "categoría"
        verbose_name_plural = "categorías"
        ordering = ["edicion", "orden", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["edicion", "nombre"], name="categoria_unica_por_edicion"),
        ]

    def __str__(self):
        return f"{self.nombre} · {self.edicion.anio}"

    def get_absolute_url(self):
        return reverse("festival:categoria_detalle", args=[self.pk])


class VotacionPublicaQuerySet(models.QuerySet):
    def publicas(self):
        # no muestra borradores ni categorías/ediciones ocultas
        return self.exclude(estado=Votacion.Estado.BORRADOR).filter(
            categoria__activa=True, categoria__edicion__activa=True,
        )


class Votacion(ModeloConFechas):
    class Estado(models.TextChoices):
        BORRADOR = "borrador", "Borrador"
        ABIERTA = "abierta", "Abierta"
        CERRADA = "cerrada", "Cerrada"

    class Modalidad(models.TextChoices):
        PUBLICO = "publico", "Votación del público"
        JURADO = "jurado", "Votación de jurado"

    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name="votaciones", verbose_name="categoría",
    )
    titulo = models.CharField("título", max_length=200)
    descripcion = models.TextField("descripción", blank=True)
    modalidad = models.CharField("modalidad", max_length=10, choices=Modalidad.choices, default=Modalidad.PUBLICO)
    estado = models.CharField("estado", max_length=10, choices=Estado.choices, default=Estado.BORRADOR)
    fecha_apertura = models.DateTimeField("apertura", null=True, blank=True)
    fecha_cierre = models.DateTimeField("cierre", null=True, blank=True)
    votos_por_usuario = models.PositiveSmallIntegerField(
        "votos por usuario", default=1,
        help_text="Límite de votos por cuenta. Regla pendiente de validación con la Fundación (PC-06).",
    )
    publicar_resultados = models.BooleanField(
        "publicar resultados", default=False,
        help_text="Política de publicación pendiente de validación (RN-06, PC-09).",
    )

    objects = VotacionPublicaQuerySet.as_manager()

    class Meta:
        verbose_name = "votación"
        verbose_name_plural = "votaciones"
        ordering = ["categoria", "titulo"]
        constraints = [
            models.UniqueConstraint(fields=["categoria", "titulo"], name="votacion_unica_por_categoria"),
            models.CheckConstraint(
                condition=Q(fecha_cierre__isnull=True) | Q(fecha_apertura__isnull=True) | Q(fecha_cierre__gt=models.F("fecha_apertura")),
                name="votacion_cierre_despues_apertura",
            ),
            models.CheckConstraint(condition=Q(votos_por_usuario__gte=1), name="votacion_minimo_un_voto"),
        ]

    def __str__(self):
        return self.titulo

    def clean(self):
        if self.fecha_apertura and self.fecha_cierre and self.fecha_cierre <= self.fecha_apertura:
            raise ValidationError({"fecha_cierre": "El cierre debe ser posterior a la apertura."})

    def get_absolute_url(self):
        return reverse("festival:votacion_detalle", args=[self.pk])

    @property
    def edicion(self):
        return self.categoria.edicion

    def puede_abrirse(self):
        # RN-02: minimo dos opciones activas
        return self.opciones.filter(activa=True).count() >= 2

    @property
    def en_periodo(self):
        ahora = timezone.now()
        if self.fecha_apertura and ahora < self.fecha_apertura:
            return False
        if self.fecha_cierre and ahora > self.fecha_cierre:
            return False
        return True

    @property
    def acepta_votos(self):
        return self.estado == self.Estado.ABIERTA and self.en_periodo


class Opcion(ModeloConFechas):
    votacion = models.ForeignKey(
        Votacion, on_delete=models.CASCADE, related_name="opciones", verbose_name="votación",
    )
    nombre = models.CharField("nombre", max_length=150)
    descripcion = models.CharField("descripción", max_length=255, blank=True)
    orden = models.PositiveSmallIntegerField("orden", default=0)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "opción"
        verbose_name_plural = "opciones"
        ordering = ["votacion", "orden", "nombre"]
        constraints = [
            models.UniqueConstraint(fields=["votacion", "nombre"], name="opcion_unica_por_votacion"),
        ]

    def __str__(self):
        return self.nombre


class Voto(models.Model):
    # el registro de votos se completa en la entrega 3
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="votos", verbose_name="usuario",
    )
    votacion = models.ForeignKey(Votacion, on_delete=models.PROTECT, related_name="votos", verbose_name="votación")
    opcion = models.ForeignKey(Opcion, on_delete=models.PROTECT, related_name="votos", verbose_name="opción")
    fecha = models.DateTimeField("fecha", auto_now_add=True)

    class Meta:
        verbose_name = "voto"
        verbose_name_plural = "votos"
        ordering = ["-fecha"]
        indexes = [models.Index(fields=["usuario", "votacion"], name="voto_usuario_votacion_idx")]

    def __str__(self):
        return f"{self.usuario} → {self.opcion} ({self.votacion})"

    def clean(self):
        if self.opcion_id and self.votacion_id and self.opcion.votacion_id != self.votacion_id:
            raise ValidationError({"opcion": "La opción no pertenece a esta votación."})
