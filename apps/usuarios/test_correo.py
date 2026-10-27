"""Pruebas del correo de recuperación de contraseña (HU-12)."""
import json
import smtplib
from unittest import mock

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import Rol
from apps.usuarios import services
from apps.usuarios.models import TokenRecuperacion, Usuario

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


@override_settings(EMAIL_BACKEND=LOCMEM, SITE_URL="")
class CorreoRecuperacionTests(TestCase):
    def setUp(self):
        rol, _ = Rol.objects.get_or_create(nombre_rol="Estudiante")
        self.usuario = Usuario.objects.create_user(
            "ana@correo.com", "clave1234", nombre="Ana", apellido="Pérez", rol=rol)

    def _solicitar(self, correo="ana@correo.com"):
        return services.solicitar_recuperacion(correo, lambda ruta: f"http://testserver{ruta}")

    def test_envia_texto_y_html_con_el_enlace(self):
        token = self._solicitar()
        self.assertEqual(len(mail.outbox), 1)
        correo = mail.outbox[0]
        self.assertEqual(correo.to, ["ana@correo.com"])
        enlace = f"http://testserver{reverse('usuarios:restablecer_password', args=[token])}"
        self.assertIn(enlace, correo.body)
        self.assertEqual(correo.alternatives[0].mimetype, "text/html")
        self.assertIn(enlace, correo.alternatives[0].content)
        self.assertIn("30 minutos", correo.body)

    def test_la_busqueda_del_correo_no_distingue_mayusculas(self):
        self._solicitar("ANA@CORREO.COM")
        self.assertEqual(len(mail.outbox), 1)

    def test_correo_no_registrado_no_envia_nada(self):
        self.assertIsNone(self._solicitar("nadie@correo.com"))
        self.assertEqual(len(mail.outbox), 0)

    def test_cuenta_desactivada_no_recibe_correo(self):
        Usuario.objects.filter(pk=self.usuario.pk).update(estado=False)
        self.assertIsNone(self._solicitar())
        self.assertEqual(len(mail.outbox), 0)

    @override_settings(SITE_URL="https://netbean.example.com/")
    def test_site_url_reemplaza_el_dominio_del_enlace(self):
        token = self._solicitar()
        esperado = f"https://netbean.example.com{reverse('usuarios:restablecer_password', args=[token])}"
        self.assertIn(esperado, mail.outbox[0].body)

    def test_un_fallo_de_smtp_no_rompe_la_solicitud_y_se_registra(self):
        with mock.patch("apps.usuarios.services.EmailMultiAlternatives.send", side_effect=smtplib.SMTPException("caído")):
            with self.assertLogs("apps.usuarios.services", level="ERROR"):
                token = self._solicitar()
        self.assertIsNotNone(token)
        self.assertTrue(TokenRecuperacion.objects.filter(usuario=self.usuario, usado=False).exists())

    def test_la_api_responde_lo_mismo_aunque_falle_el_envio(self):
        url = reverse("api_recuperar_password")
        with mock.patch("apps.usuarios.services.EmailMultiAlternatives.send", side_effect=smtplib.SMTPException("caído")):
            with self.assertLogs("apps.usuarios.services", level="ERROR"):
                falla = self.client.post(url, json.dumps({"correo": "ana@correo.com"}), content_type="application/json")
        inexistente = self.client.post(url, json.dumps({"correo": "nadie@correo.com"}), content_type="application/json")
        self.assertEqual(falla.status_code, 200)
        self.assertEqual(falla.json(), inexistente.json())
