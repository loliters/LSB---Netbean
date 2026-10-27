"""Pruebas del dashboard, el perfil, el panel del administrador y los datos de demostración."""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Rol
from apps.gamificacion.models import UsuarioLogro
from apps.usuarios.models import EstadisticasUsuario, Usuario


class DemoYPerfilTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_demo", verbosity=0)
        cls.demo = Usuario.objects.get(correo="estudiante.demo@netbean.com")

    def test_demo_tiene_racha_xp_e_insignias_de_modulo(self):
        estadisticas = EstadisticasUsuario.objects.get(usuario=self.demo)
        self.assertEqual(estadisticas.racha_dias, 6)
        self.assertGreater(estadisticas.xp_total, 0)
        nombres = set(UsuarioLogro.objects.filter(usuario=self.demo).values_list("logro__nombre", flat=True))
        self.assertTrue({"Maestro de Vocales", "Experto en Números", "Racha de Fuego", "Diez prácticas"} <= nombres)

    def test_demo_es_idempotente_sin_reiniciar(self):
        call_command("cargar_demo", verbosity=0)
        self.assertEqual(Usuario.objects.filter(correo="estudiante.demo@netbean.com").count(), 1)

    def test_perfil_muestra_insignias_con_fecha(self):
        self.client.force_login(self.demo)
        respuesta = self.client.get(reverse("usuarios:perfil"))
        self.assertContains(respuesta, "Maestro de Vocales")
        self.assertContains(respuesta, "Insignias ganadas")
        self.assertContains(respuesta, "Actividad reciente")

    def test_dashboard_estudiante_tiene_grafico_y_sin_mascota(self):
        self.client.force_login(self.demo)
        respuesta = self.client.get(reverse("usuarios:panel_estudiante"))
        self.assertContains(respuesta, "datos-semana")
        self.assertNotContains(respuesta, "data-ugg")
        self.assertContains(respuesta, "Tiempo de práctica")


class PanelAdminTests(TestCase):
    def setUp(self):
        call_command("cargar_demo", verbosity=0)
        self.admin = Usuario.objects.create_user(
            "admin@correo.com", "admin1234", nombre="Lolo", apellido="Admin",
            rol=Rol.objects.get_or_create(nombre_rol="Administrador")[0],
        )
        self.client.force_login(self.admin)

    def test_panel_admin_lista_estudiantes_y_modulos(self):
        respuesta = self.client.get(reverse("usuarios:panel_admin"))
        self.assertContains(respuesta, "estudiante.demo@netbean.com")
        self.assertContains(respuesta, "data-filtro-texto")
        self.assertContains(respuesta, "Control de módulos")
        self.assertContains(respuesta, "Vocales")
