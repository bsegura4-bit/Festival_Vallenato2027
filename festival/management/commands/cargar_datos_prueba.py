# Uso: python manage.py cargar_datos_prueba [--reiniciar]
# Los participantes son ficticios (RN-09).
from datetime import date, datetime, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from festival.models import Categoria, Edicion, Opcion, Votacion, Voto

ABIERTA, CERRADA, BORRADOR = Votacion.Estado.ABIERTA, Votacion.Estado.CERRADA, Votacion.Estado.BORRADOR

EDICIONES = [
    {
        "anio": 2027, "numero": 60, "nombre": "60.º Festival de la Leyenda Vallenata",
        "fecha_inicio": date(2027, 4, 28), "fecha_fin": date(2027, 5, 2), "activa": True,
        "descripcion": "Edición de prueba para el sistema de votaciones. Consulta las votaciones del público, "
                       "elige tu opción favorita y sigue los concursos del Festival.",
        "categorias": [
            ("Acordeón Profesional", "Concurso de conjuntos de música tradicional vallenata, categoría profesional.", [
                ("Votación del público · Acordeonero profesional favorito", ABIERTA, "publico",
                 ["Concursante de prueba 1", "Concursante de prueba 2", "Concursante de prueba 3", "Concursante de prueba 4"]),
                ("Mejor interpretación de paseo", BORRADOR, "jurado", ["Concursante de prueba 1"]),
            ]),
            ("Acordeón Aficionado", "Concurso de acordeoneros aficionados.", [
                ("Votación del público · Acordeonero aficionado favorito", ABIERTA, "publico",
                 ["Aficionado de prueba A", "Aficionado de prueba B", "Aficionado de prueba C"]),
            ]),
            ("Acordeonera Mayor", "Concurso para mujeres acordeoneras.", [
                ("Votación del público · Acordeonera favorita", ABIERTA, "publico",
                 ["Acordeonera de prueba 1", "Acordeonera de prueba 2", "Acordeonera de prueba 3"]),
            ]),
            ("Canción Vallenata Inédita", "Obras inéditas de compositores y autores.", [
                ("Canción inédita favorita del público", ABIERTA, "publico",
                 ["«Canción de prueba 1»", "«Canción de prueba 2»", "«Canción de prueba 3»", "«Canción de prueba 4»", "«Canción de prueba 5»"]),
            ]),
            ("Piquería Mayor", "Improvisación de cuartetas y décimas.", [
                ("Mejor piquería de la noche", CERRADA, "publico",
                 ["Piquero de prueba 1", "Piquero de prueba 2"]),
            ]),
            ("Piloneras Mayor", "Grupos de piloneras, categoría mayores.", [
                ("Grupo de piloneras favorito", ABIERTA, "publico",
                 ["Grupo de piloneras de prueba 1", "Grupo de piloneras de prueba 2", "Grupo de piloneras de prueba 3"]),
            ]),
        ],
    },
    {
        "anio": 2026, "numero": 59, "nombre": "59.º Festival de la Leyenda Vallenata",
        "fecha_inicio": date(2026, 4, 29), "fecha_fin": date(2026, 5, 3), "activa": True,
        "descripcion": "Edición anterior registrada para demostrar el manejo de varias ediciones.",
        "categorias": [
            ("Acordeón Profesional", "Concurso de la edición anterior (datos de prueba).", [
                ("Votación del público 2026 · Acordeonero favorito", CERRADA, "publico",
                 ["Concursante 2026 A", "Concursante 2026 B", "Concursante 2026 C"]),
            ]),
            ("Canción Vallenata Inédita", "Concurso de la edición anterior (datos de prueba).", [
                ("Canción inédita favorita 2026", CERRADA, "publico", ["«Canción 2026 A»", "«Canción 2026 B»"]),
            ]),
        ],
    },
]


class Command(BaseCommand):
    help = "Crea ediciones, categorías, votaciones y opciones de prueba en la base de datos."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true", help="Borra los datos del festival antes de cargarlos.")

    @transaction.atomic
    def handle(self, *args, **opciones):
        if opciones["reiniciar"]:
            Voto.objects.all().delete()
            Opcion.objects.all().delete()
            Votacion.objects.all().delete()
            Categoria.objects.all().delete()
            Edicion.objects.all().delete()
            self.stdout.write("Datos anteriores eliminados.")

        ahora = timezone.now().replace(minute=0, second=0, microsecond=0)
        conteo = {"ediciones": 0, "categorias": 0, "votaciones": 0, "opciones": 0}

        for datos in EDICIONES:
            datos = dict(datos)
            categorias = datos.pop("categorias")
            edicion, _ = Edicion.objects.update_or_create(anio=datos.pop("anio"), defaults=datos)
            conteo["ediciones"] += 1

            for orden, (nombre, descripcion, votaciones) in enumerate(categorias, start=1):
                categoria, _ = Categoria.objects.update_or_create(
                    edicion=edicion, nombre=nombre, defaults={"descripcion": descripcion, "orden": orden, "activa": True},
                )
                conteo["categorias"] += 1

                for titulo, estado, modalidad, nombres in votaciones:
                    if edicion.anio < 2027:
                        inicio = timezone.make_aware(datetime(edicion.anio, 4, 29, 8))
                        apertura, cierre = inicio, inicio + timedelta(days=4)
                    elif estado == CERRADA:
                        apertura, cierre = ahora - timedelta(days=10), ahora - timedelta(days=1)
                    else:
                        apertura = ahora - timedelta(days=1)
                        cierre = timezone.make_aware(datetime(2027, 5, 2, 23, 59))
                    votacion, _ = Votacion.objects.update_or_create(
                        categoria=categoria, titulo=titulo,
                        defaults={
                            "estado": estado, "modalidad": modalidad,
                            "descripcion": f"Votación de prueba de la categoría {nombre}. "
                                           "Las reglas definitivas dependen de la validación con la Fundación.",
                            "fecha_apertura": apertura, "fecha_cierre": cierre,
                            "votos_por_usuario": 1, "publicar_resultados": estado == CERRADA,
                        },
                    )
                    conteo["votaciones"] += 1
                    for i, nombre_opcion in enumerate(nombres, start=1):
                        Opcion.objects.update_or_create(
                            votacion=votacion, nombre=nombre_opcion,
                            defaults={"descripcion": "Participante ficticio para pruebas", "orden": i, "activa": True},
                        )
                        conteo["opciones"] += 1

        resumen = ", ".join(f"{v} {k}" for k, v in conteo.items())
        self.stdout.write(self.style.SUCCESS(f"Datos de prueba listos: {resumen}."))
