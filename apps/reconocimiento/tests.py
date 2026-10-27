"""Pruebas mínimas del endpoint de predicción (HU-05)."""
import json
from unittest import mock

from django.test import TestCase
from django.urls import reverse

from apps.core.models import Rol
from apps.usuarios.models import Usuario
from ia.predictor import Prediccion
from ia.preprocesador import decodificar_base64

FRAME_FALSO = "data:image/jpeg;base64,AAAA"


class PrediccionEndpointTests(TestCase):
    def setUp(self):
        rol = Rol.objects.create(nombre_rol="Estudiante")
        self.usuario = Usuario.objects.create_user(
            "ana@correo.com", "clave1234", nombre="Ana", apellido="Pérez", rol=rol
        )
        self.client.force_login(self.usuario)
        self.url = reverse("reconocimiento:predecir")

    def _post(self, cuerpo):
        return self.client.post(self.url, json.dumps(cuerpo), content_type="application/json")

    @mock.patch("apps.reconocimiento.views.predecir_desde_base64")
    def test_hu05_ca2_prediccion_responde_200_con_letra(self, predecir):
        predecir.return_value = Prediccion(letra="B", confianza=0.91, mano_detectada=True)
        respuesta = self._post({"frame": FRAME_FALSO})
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.json()["letra"], "B")
        predecir.assert_called_once_with(FRAME_FALSO, modo="letra")

    def test_hu05_ca5_sin_frame_responde_400(self):
        self.assertEqual(self._post({}).status_code, 400)

    def test_prediccion_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self._post({"frame": FRAME_FALSO}).status_code, 302)

    def test_preprocesador_base64_invalido_devuelve_none(self):
        self.assertIsNone(decodificar_base64("esto-no-es-imagen"))
