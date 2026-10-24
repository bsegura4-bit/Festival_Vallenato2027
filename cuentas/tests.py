from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

Usuario = get_user_model()


class AutenticacionTests(TestCase):
    datos = {
        "first_name": "Ana", "last_name": "Pérez", "email": "Ana@Correo.com",
        "password1": "Vallenato#2027", "password2": "Vallenato#2027", "acepta_datos": "on",
    }

    def test_registro_crea_usuario_e_inicia_sesion(self):
        r = self.client.post(reverse("cuentas:registro"), self.datos, follow=True)
        self.assertRedirects(r, reverse("festival:inicio"))
        usuario = Usuario.objects.get(email="ana@correo.com")
        self.assertTrue(usuario.check_password("Vallenato#2027"))
        self.assertNotEqual(usuario.password, "Vallenato#2027")  # se guarda con hash
        self.assertEqual(int(self.client.session["_auth_user_id"]), usuario.pk)

    def test_registro_exige_aceptar_datos(self):
        datos = {**self.datos, "acepta_datos": ""}
        r = self.client.post(reverse("cuentas:registro"), datos)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.exists())

    def test_registro_rechaza_correo_repetido(self):
        Usuario.objects.create_user("ana@correo.com", "ana@correo.com", "OtraClave#99")
        r = self.client.post(reverse("cuentas:registro"), self.datos)
        self.assertContains(r, "Ya existe una cuenta con este correo")

    def test_registro_rechaza_clave_debil(self):
        datos = {**self.datos, "password1": "12345678", "password2": "12345678"}
        self.client.post(reverse("cuentas:registro"), datos)
        self.assertFalse(Usuario.objects.exists())

    def test_login_con_correo_y_logout(self):
        Usuario.objects.create_user("ana@correo.com", "ana@correo.com", "Vallenato#2027", first_name="Ana")
        r = self.client.post(reverse("cuentas:login"), {"username": "ANA@correo.com", "password": "Vallenato#2027"})
        self.assertRedirects(r, reverse("festival:inicio"))
        self.assertIn("_auth_user_id", self.client.session)
        r = self.client.post(reverse("cuentas:logout"))
        self.assertRedirects(r, reverse("festival:inicio"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_login_con_clave_incorrecta(self):
        Usuario.objects.create_user("ana@correo.com", "ana@correo.com", "Vallenato#2027")
        r = self.client.post(reverse("cuentas:login"), {"username": "ana@correo.com", "password": "mala"})
        self.assertContains(r, "Correo o contraseña incorrectos")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_perfil_requiere_sesion(self):
        r = self.client.get(reverse("cuentas:perfil"))
        self.assertRedirects(r, reverse("cuentas:login") + "?next=" + reverse("cuentas:perfil"))
