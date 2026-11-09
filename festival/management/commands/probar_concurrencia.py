# Uso: python manage.py probar_concurrencia --usuario votante2 [--hilos 5]
# Envía varios votos al mismo tiempo (uno por hilo y conexión a MySQL) en la
# misma categoría para comprobar que solo queda uno guardado (CP-09).
import threading

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from festival.models import Votacion, Voto
from festival.votos import VotoRechazado, registrar_voto


class Command(BaseCommand):
    help = "Prueba de solicitudes simultáneas de voto en una misma categoría."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Nombre de usuario que vota.")
        parser.add_argument("--hilos", type=int, default=5)
        parser.add_argument("--categoria", help="Nombre de la categoría (por defecto la primera con dos votaciones abiertas).")

    def handle(self, *args, **opciones):
        usuario = get_user_model().objects.filter(username=opciones["usuario"]).first()
        if usuario is None:
            raise CommandError("No existe ese usuario.")

        abiertas = [v for v in Votacion.objects.publicas().filter(estado=Votacion.Estado.ABIERTA)
                    .select_related("categoria").order_by("categoria__orden") if v.acepta_votos]
        if opciones["categoria"]:
            abiertas = [v for v in abiertas if v.categoria.nombre == opciones["categoria"]]
        if not abiertas:
            raise CommandError("No hay votaciones abiertas para probar.")
        categoria = abiertas[0].categoria
        votaciones = [v for v in abiertas if v.categoria_id == categoria.pk]

        if Voto.objects.filter(usuario=usuario, categoria=categoria).exists():
            raise CommandError(f"{usuario} ya votó en {categoria.nombre}; usa otro usuario o categoría.")

        # cada hilo vota por una opción distinta, alternando entre los subeventos de la categoría
        envios = []
        for i in range(opciones["hilos"]):
            votacion = votaciones[i % len(votaciones)]
            ops = list(votacion.opciones.filter(activa=True))
            envios.append((votacion, ops[i % len(ops)]))

        barrera = threading.Barrier(len(envios))
        resultados = [None] * len(envios)

        def votar(i, votacion, opcion):
            try:
                barrera.wait()
                registrar_voto(usuario, votacion.pk, opcion.pk)
                resultados[i] = "ACEPTADO"
            except VotoRechazado as error:
                resultados[i] = f"rechazado: {error}"
            finally:
                connection.close()

        hilos = [threading.Thread(target=votar, args=(i, v, o)) for i, (v, o) in enumerate(envios)]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        self.stdout.write(f"Categoría: {categoria.nombre} ({len(envios)} solicitudes simultáneas)")
        for i, ((votacion, opcion), resultado) in enumerate(zip(envios, resultados), start=1):
            self.stdout.write(f"  #{i} {votacion.titulo} → {opcion.nombre}: {resultado}")
        guardados = Voto.objects.filter(usuario=usuario, categoria=categoria).count()
        estilo = self.style.SUCCESS if guardados == 1 else self.style.ERROR
        self.stdout.write(estilo(f"Votos guardados en MySQL para {usuario} en esta categoría: {guardados}"))
