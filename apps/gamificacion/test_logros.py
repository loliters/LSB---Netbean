"""Pruebas de logros (HU-11)."""
from datetime import timedelta
from decimal import Decimal

from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, Rol, TipoSena
from apps.usuarios.models import EstadisticasUsuario, Usuario

from . import services
from .models import UsuarioLogro


class LogrosTests(TestCase):
    def setUp(self):
        call_command("cargar_logros", verbosity=0)
        rol = Rol.objects.create(nombre_rol="Estudiante")
        self.usuario = Usuario.objects.create_user("ana@correo.com", "clave1234", nombre="Ana", apellido="Pérez", rol=rol)
        dificultad = Dificultad.objects.create(nivel=1, nombre="Básico", multiplicador_xp=Decimal("1"))
        modulo = Modulo.objects.create(categoria=Categoria.objects.create(nombre="Alfabeto"), nombre="Alfabeto", orden=1)
        leccion = Leccion.objects.create(modulo=modulo, nombre="Letras", orden=1)
        tipo = TipoSena.objects.create(nombre="Estática")
        self.sena = Sena.objects.create(leccion=leccion, tipo_sena=tipo, dificultad=dificultad, nombre="A", ruta_imagen="senas/a.png")
        self.otra = Sena.objects.create(leccion=leccion, tipo_sena=tipo, dificultad=dificultad, nombre="B", ruta_imagen="senas/b.png")

    def _intentar(self, sena=None, letra="A", confianza=0.9):
        return services.registrar_intento(usuario=self.usuario, sena=sena or self.sena, letra_predicha=letra, confianza=confianza)

    def test_hu11_ca1_primer_paso_al_primer_intento_suma_xp_extra(self):
        resultado = self._intentar()
        self.assertIn("Primer paso", [l["nombre"] for l in resultado["logros_nuevos"]])
        self.assertEqual(EstadisticasUsuario.objects.get(usuario=self.usuario).xp_total, 30 + 10)

    def test_hu11_ca1_logro_tambien_en_intento_fallido(self):
        resultado = self._intentar(letra="Z")
        self.assertIn("Primer paso", [l["nombre"] for l in resultado["logros_nuevos"]])

    def test_hu11_ca2_logro_no_se_otorga_dos_veces(self):
        self._intentar()
        segundo = self._intentar(sena=self.otra, letra="B")
        self.assertNotIn("Primer paso", [l["nombre"] for l in segundo["logros_nuevos"]])
        self.assertEqual(UsuarioLogro.objects.filter(usuario=self.usuario, logro__nombre="Primer paso").count(), 1)

    def test_hu11_logro_de_racha_al_tercer_dia(self):
        EstadisticasUsuario.objects.create(
            usuario=self.usuario, racha_dias=2, ultima_practica=timezone.localdate() - timedelta(days=1)
        )
        resultado = self._intentar()
        self.assertIn("Racha de 3 días", [l["nombre"] for l in resultado["logros_nuevos"]])

    def test_hu11_pantalla_muestra_obtenidos_y_avance(self):
        self._intentar()
        self.client.force_login(self.usuario)
        respuesta = self.client.get(reverse("gamificacion:logros"))
        self.assertContains(respuesta, "Primer paso")
        self.assertContains(respuesta, "Obtenido el")
        self.assertContains(respuesta, "1/5")  # Primeras 5 señas: 1 dominada
