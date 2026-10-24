from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Categoria, Edicion, Opcion, Votacion, Voto


class BaseDatos(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.edicion = Edicion.objects.create(nombre="Festival de prueba", anio=2027, numero=60)
        cls.categoria = Categoria.objects.create(edicion=cls.edicion, nombre="Acordeón Profesional")
        cls.abierta = Votacion.objects.create(
            categoria=cls.categoria, titulo="Favorito del público", estado=Votacion.Estado.ABIERTA,
            fecha_apertura=timezone.now() - timedelta(days=1), fecha_cierre=timezone.now() + timedelta(days=5),
        )
        cls.op1 = Opcion.objects.create(votacion=cls.abierta, nombre="Opción A")
        cls.op2 = Opcion.objects.create(votacion=cls.abierta, nombre="Opción B")
        cls.borrador = Votacion.objects.create(categoria=cls.categoria, titulo="Votación oculta")


class ModelosTests(BaseDatos):
    def test_jerarquia_edicion_categoria_votacion_opcion(self):
        self.assertEqual(self.op1.votacion.categoria.edicion, self.edicion)
        self.assertEqual(self.edicion.categorias.count(), 1)
        self.assertEqual(self.categoria.votaciones.count(), 2)
        self.assertEqual(self.abierta.opciones.count(), 2)

    def test_categoria_unica_por_edicion(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Categoria.objects.create(edicion=self.edicion, nombre="Acordeón Profesional")

    def test_misma_categoria_en_otra_edicion_si_se_permite(self):
        otra = Edicion.objects.create(nombre="Festival anterior", anio=2026)
        Categoria.objects.create(edicion=otra, nombre="Acordeón Profesional")

    def test_cierre_debe_ser_posterior_a_apertura(self):
        ahora = timezone.now()
        v = Votacion(categoria=self.categoria, titulo="Mal configurada", fecha_apertura=ahora, fecha_cierre=ahora - timedelta(hours=1))
        with self.assertRaises(ValidationError):
            v.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            v.save()

    def test_no_se_puede_borrar_edicion_con_categorias(self):
        from django.db.models import ProtectedError
        with self.assertRaises(ProtectedError):
            self.edicion.delete()

    def test_regla_minimo_dos_opciones(self):
        self.assertTrue(self.abierta.puede_abrirse())
        self.assertFalse(self.borrador.puede_abrirse())

    def test_acepta_votos_solo_abierta_y_en_periodo(self):
        self.assertTrue(self.abierta.acepta_votos)
        self.assertFalse(self.borrador.acepta_votos)
        self.abierta.fecha_cierre = timezone.now() - timedelta(minutes=1)
        self.abierta.fecha_apertura = timezone.now() - timedelta(days=2)
        self.assertFalse(self.abierta.acepta_votos)

    def test_voto_con_opcion_de_otra_votacion_es_invalido(self):
        usuario = get_user_model().objects.create_user("votante", "v@correo.com", "ClaveSegura123")
        otra = Opcion.objects.create(votacion=self.borrador, nombre="Opción X")
        voto = Voto(usuario=usuario, votacion=self.abierta, opcion=otra)
        with self.assertRaises(ValidationError):
            voto.full_clean()


class VistasPublicasTests(BaseDatos):
    def test_inicio_muestra_datos_de_mysql(self):
        r = self.client.get(reverse("festival:inicio"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Favorito del público")
        self.assertContains(r, "Acordeón Profesional")

    def test_paginas_publicas_responden(self):
        for url in [
            reverse("festival:ediciones"),
            reverse("festival:edicion_detalle", args=[2027]),
            reverse("festival:categorias"),
            reverse("festival:categoria_detalle", args=[self.categoria.pk]),
            reverse("festival:votaciones"),
            reverse("festival:votacion_detalle", args=[self.abierta.pk]),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_borradores_no_son_publicos(self):
        r = self.client.get(reverse("festival:votaciones"))
        self.assertNotContains(r, "Votación oculta")
        r = self.client.get(reverse("festival:votacion_detalle", args=[self.borrador.pk]))
        self.assertEqual(r.status_code, 404)

    def test_detalle_lista_opciones(self):
        r = self.client.get(reverse("festival:votacion_detalle", args=[self.abierta.pk]))
        self.assertContains(r, "Opción A")
        self.assertContains(r, "Opción B")

    def test_filtro_por_estado(self):
        Votacion.objects.create(categoria=self.categoria, titulo="Ya cerrada", estado=Votacion.Estado.CERRADA)
        r = self.client.get(reverse("festival:votaciones") + "?estado=cerrada")
        self.assertContains(r, "Ya cerrada")
        self.assertNotContains(r, "Favorito del público")

    def test_edicion_oculta_da_404(self):
        Edicion.objects.create(nombre="Oculta", anio=2030, activa=False)
        self.assertEqual(self.client.get(reverse("festival:edicion_detalle", args=[2030])).status_code, 404)


class AdminTests(BaseDatos):
    def setUp(self):
        self.admin = get_user_model().objects.create_superuser("admin", "admin@correo.com", "ClaveAdmin123")
        self.client.force_login(self.admin)

    def test_listados_del_admin(self):
        for modelo in ["edicion", "categoria", "votacion", "opcion", "voto"]:
            with self.subTest(modelo=modelo):
                self.assertEqual(self.client.get(reverse(f"admin:festival_{modelo}_changelist")).status_code, 200)

    def test_accion_abrir_respeta_minimo_de_opciones(self):
        url = reverse("admin:festival_votacion_changelist")
        self.client.post(url, {"action": "abrir_votaciones", "_selected_action": [self.borrador.pk]})
        self.borrador.refresh_from_db()
        self.assertEqual(self.borrador.estado, Votacion.Estado.BORRADOR)

    def test_usuario_normal_no_entra_al_admin(self):
        self.client.logout()
        usuario = get_user_model().objects.create_user("votante", "v@correo.com", "ClaveSegura123")
        self.client.force_login(usuario)
        r = self.client.get(reverse("admin:index"))
        self.assertEqual(r.status_code, 302)


class DatosDePruebaTests(TestCase):
    def test_comando_carga_datos(self):
        call_command("cargar_datos_prueba", verbosity=0)
        self.assertEqual(Edicion.objects.count(), 2)
        self.assertGreaterEqual(Votacion.objects.filter(estado=Votacion.Estado.ABIERTA).count(), 1)
        call_command("cargar_datos_prueba", verbosity=0)
        self.assertEqual(Edicion.objects.count(), 2)
