"""Pruebas del módulo de votaciones (casos CP-01 a CP-10 de la entrega 3)."""
import json
import threading
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection, transaction
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, Edicion, Opcion, Votacion, Voto
from .votos import VotoRechazado, registrar_voto


def crear_datos(cls):
    ahora = timezone.now()
    cls.edicion = Edicion.objects.create(nombre="Festival de prueba", anio=2027)
    cls.cat_a = Categoria.objects.create(edicion=cls.edicion, nombre="Acordeón Profesional", orden=1)
    cls.cat_b = Categoria.objects.create(edicion=cls.edicion, nombre="Canción Inédita", orden=2)
    periodo = {"fecha_apertura": ahora - timedelta(days=1), "fecha_cierre": ahora + timedelta(days=5)}
    cls.vot_a1 = Votacion.objects.create(categoria=cls.cat_a, titulo="Favorito", estado=Votacion.Estado.ABIERTA, **periodo)
    cls.vot_a2 = Votacion.objects.create(categoria=cls.cat_a, titulo="Subevento", estado=Votacion.Estado.ABIERTA, **periodo)
    cls.vot_b = Votacion.objects.create(categoria=cls.cat_b, titulo="Canción favorita", estado=Votacion.Estado.ABIERTA, **periodo)
    cls.vot_cerrada = Votacion.objects.create(categoria=cls.cat_b, titulo="Cerrada", estado=Votacion.Estado.CERRADA, **periodo)
    cls.a1 = Opcion.objects.create(votacion=cls.vot_a1, nombre="Concursante 1")
    cls.a1b = Opcion.objects.create(votacion=cls.vot_a1, nombre="Concursante 2")
    cls.a2 = Opcion.objects.create(votacion=cls.vot_a2, nombre="Concursante 3")
    Opcion.objects.create(votacion=cls.vot_a2, nombre="Concursante 4")
    cls.b1 = Opcion.objects.create(votacion=cls.vot_b, nombre="Canción 1")
    Opcion.objects.create(votacion=cls.vot_b, nombre="Canción 2")
    cls.cerrada_op = Opcion.objects.create(votacion=cls.vot_cerrada, nombre="Canción X")


class VotosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        crear_datos(cls)
        Usuario = get_user_model()
        cls.usuario = Usuario.objects.create_user("votante", "v@correo.com", "ClaveSegura123")
        cls.admin = Usuario.objects.create_superuser("admin", "a@correo.com", "ClaveAdmin123")

    def votar(self, votacion, opcion, confirmar=True):
        datos = {"opcion": opcion.pk}
        if confirmar:
            datos["confirmar"] = "1"
        return self.client.post(reverse("festival:votar", args=[votacion.pk]), datos)

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_cp01_voto_valido_se_guarda(self):
        r = self.votar(self.vot_a1, self.a1, confirmar=False)
        self.assertContains(r, "Confirmar voto")
        self.assertEqual(Voto.objects.count(), 0)  # aún no se guarda
        r = self.votar(self.vot_a1, self.a1)
        self.assertRedirects(r, reverse("festival:mis_votos"))
        voto = Voto.objects.get()
        self.assertEqual((voto.usuario, voto.opcion, voto.categoria, voto.edicion), (self.usuario, self.a1, self.cat_a, self.edicion))

    def test_cp02_segundo_voto_misma_categoria_rechazado(self):
        self.votar(self.vot_a1, self.a1)
        r = self.votar(self.vot_a1, self.a1b, confirmar=False)  # otra opción
        r = self.votar(self.vot_a2, self.a2)  # otro subevento de la misma categoría
        self.assertEqual(Voto.objects.filter(usuario=self.usuario, categoria=self.cat_a).count(), 1)
        r = self.client.get(reverse("festival:votacion_detalle", args=[self.vot_a2.pk]))
        self.assertContains(r, "Ya votaste en esta categoría")

    def test_cp03_voto_en_otra_categoria_permitido(self):
        self.votar(self.vot_a1, self.a1)
        self.votar(self.vot_b, self.b1)
        self.assertEqual(Voto.objects.filter(usuario=self.usuario).count(), 2)

    def test_cp04_anonimo_debe_iniciar_sesion(self):
        self.client.logout()
        r = self.votar(self.vot_a1, self.a1)
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("cuentas:login"), r["Location"])
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp05_votacion_no_habilitada_rechazada(self):
        self.votar(self.vot_cerrada, self.cerrada_op)
        borrador = Votacion.objects.create(categoria=self.cat_a, titulo="Borrador")
        op = Opcion.objects.create(votacion=borrador, nombre="Z")
        r = self.votar(borrador, op)
        self.assertEqual(r.status_code, 404)
        self.assertEqual(Voto.objects.count(), 0)

    def test_cp06_opcion_de_otra_categoria_rechazada(self):
        r = self.votar(self.vot_a1, self.b1)
        self.assertEqual(Voto.objects.count(), 0)
        r = self.client.get(r["Location"])
        self.assertContains(r, "no pertenece a esta votación")

    def test_cp07_mis_votos_muestra_registros(self):
        self.votar(self.vot_a1, self.a1)
        r = self.client.get(reverse("festival:mis_votos"))
        self.assertContains(r, "Acordeón Profesional")
        self.assertContains(r, "Concursante 1")
        self.assertContains(r, "Canción Inédita")  # aparece como pendiente

    def test_cp08_admin_consulta_votos(self):
        self.votar(self.vot_a1, self.a1)
        self.client.force_login(self.admin)
        r = self.client.get(reverse("admin:festival_voto_changelist"))
        self.assertContains(r, "votante")
        r = self.client.get(reverse("festival:reporte_votos"))
        self.assertEqual(r.context["total_votos"], Voto.objects.count())
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("festival:reporte_votos")).status_code, 302)

    def test_cp10_api_categorias_json(self):
        r = self.client.get(reverse("festival:api_categorias"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/json; charset=utf-8")
        datos = json.loads(r.content)
        self.assertEqual(datos["edicion"]["anio"], 2027)
        nombres = [c["nombre"] for c in datos["categorias"]]
        self.assertEqual(nombres, ["Acordeón Profesional", "Canción Inédita"])
        opciones = [o["nombre"] for o in datos["categorias"][0]["votaciones"][0]["opciones"]]
        self.assertIn("Concursante 1", opciones)
        self.assertEqual(self.client.post(reverse("festival:api_categorias")).status_code, 405)

    def test_restriccion_unica_en_la_base_de_datos(self):
        Voto.objects.create(usuario=self.usuario, opcion=self.a1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            Voto.objects.create(usuario=self.usuario, opcion=self.a2)

    def test_csrf_obligatorio(self):
        cliente = self.client_class(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        r = cliente.post(reverse("festival:votar", args=[self.vot_a1.pk]), {"opcion": self.a1.pk, "confirmar": "1"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(Voto.objects.count(), 0)

    def test_get_no_registra_votos(self):
        self.assertEqual(self.client.get(reverse("festival:votar", args=[self.vot_a1.pk])).status_code, 405)


class ConcurrenciaTests(TransactionTestCase):
    """CP-09: varias solicitudes al mismo tiempo, cada una con su propia conexión a MySQL."""

    def test_cp09_solicitudes_simultaneas(self):
        crear_datos(self)
        usuario = get_user_model().objects.create_user("rapido", "r@correo.com", "ClaveSegura123")
        envios = [(self.vot_a1, self.a1), (self.vot_a1, self.a1b), (self.vot_a2, self.a2), (self.vot_a1, self.a1)]
        barrera = threading.Barrier(len(envios))
        resultados = []

        def votar(votacion, opcion):
            try:
                barrera.wait()
                registrar_voto(usuario, votacion.pk, opcion.pk)
                resultados.append("ok")
            except VotoRechazado:
                resultados.append("rechazado")
            finally:
                connection.close()

        hilos = [threading.Thread(target=votar, args=e) for e in envios]
        for h in hilos:
            h.start()
        for h in hilos:
            h.join()

        self.assertEqual(resultados.count("ok"), 1)
        self.assertEqual(Voto.objects.filter(usuario=usuario, categoria=self.cat_a).count(), 1)
