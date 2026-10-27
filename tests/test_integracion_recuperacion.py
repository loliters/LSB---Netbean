"""Prueba de integración E2E de recuperación de contraseña (HU-12).

Se ejecuta contra la base de pruebas del motor configurado (PostgreSQL).
"""
import json
import re

from django.core import mail
from django.test import TestCase

from apps.core.models import Rol
from apps.usuarios.models import TokenRecuperacion, Usuario

URL_API = "/api/recuperar-password"


class RecuperarPasswordIntegracionTests(TestCase):
    def setUp(self):
        rol = Rol.objects.create(nombre_rol="Estudiante")
        self.usuario = Usuario.objects.create_user(
            "cecilia@correo.com", "clave1234", nombre="Cecilia", apellido="Pary", rol=rol
        )

    def _post(self, correo):
        return self.client.post(URL_API, json.dumps({"correo": correo}), content_type="application/json")

    def test_hu12_flujo_completo_solicitud_correo_y_restablecimiento(self):
        respuesta = self._post("cecilia@correo.com")
        self.assertEqual(respuesta.status_code, 200)
        self.assertTrue(respuesta.json()["ok"])

        registro = TokenRecuperacion.objects.get(usuario=self.usuario)
        self.assertFalse(registro.usado)
        self.assertTrue(registro.esta_vigente())
        self.assertEqual(len(mail.outbox), 1)

        enlace = re.search(r"https?://\S+/usuarios/restablecer/\S+/", mail.outbox[0].body).group(0)
        ruta = re.sub(r"^https?://[^/]+", "", enlace)
        datos = {"password1": "Nueva2026", "password2": "Nueva2026"}
        self.assertEqual(self.client.post(ruta, datos).status_code, 302)

        self.usuario.refresh_from_db()
        registro.refresh_from_db()
        self.assertTrue(self.usuario.check_password("Nueva2026"))
        self.assertTrue(registro.usado)

    def test_hu12_correo_no_registrado_responde_200_sin_token(self):
        respuesta = self._post("nadie@correo.com")
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(TokenRecuperacion.objects.exists())
        self.assertEqual(len(mail.outbox), 0)

    def test_hu12_correo_invalido_responde_400(self):
        self.assertEqual(self._post("sin-arroba").status_code, 400)
