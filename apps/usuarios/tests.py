"""Pruebas de registro, validaciones y recuperación de contraseña."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.core.models import Rol

from . import services
from .forms import RegistroForm
from .models import EstadisticasUsuario, TokenRecuperacion, Usuario

DATOS_VALIDOS = {
    "nombre": "Cecilia",
    "apellido": "Pary",
    "correo": "cecilia@correo.com",
    "password1": "Senas2026",
    "password2": "Senas2026",
}


def crear_usuario(correo="ana@correo.com", password="clave1234"):
    rol, _ = Rol.objects.get_or_create(nombre_rol="Estudiante")
    return Usuario.objects.create_user(correo, password, nombre="Ana", apellido="Pérez", rol=rol)


class RegistroTests(TestCase):
    def test_hu02_ca1_crea_estudiante_con_estadisticas(self):
        respuesta = self.client.post(reverse("usuarios:registro"), DATOS_VALIDOS)
        self.assertRedirects(respuesta, reverse("usuarios:panel_estudiante"))
        usuario = Usuario.objects.get(correo="cecilia@correo.com")
        self.assertEqual(usuario.nombre_rol, "estudiante")
        self.assertTrue(usuario.check_password("Senas2026"))
        self.assertTrue(EstadisticasUsuario.objects.filter(usuario=usuario).exists())

    def test_hu02_ca2_bloquea_correo_duplicado_sin_importar_mayusculas(self):
        crear_usuario("cecilia@correo.com")
        form = RegistroForm({**DATOS_VALIDOS, "correo": "CECILIA@correo.com"})
        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

    def test_hu02_rechaza_correo_con_formato_invalido(self):
        form = RegistroForm({**DATOS_VALIDOS, "correo": "cecilia@correo"})
        self.assertFalse(form.is_valid())
        self.assertIn("correo", form.errors)

    def test_hu02_rechaza_contrasena_corta(self):
        form = RegistroForm({**DATOS_VALIDOS, "password1": "ab12", "password2": "ab12"})
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_hu02_rechaza_contrasena_sin_numeros(self):
        form = RegistroForm({**DATOS_VALIDOS, "password1": "soloLetras", "password2": "soloLetras"})
        self.assertFalse(form.is_valid())
        self.assertIn("password1", form.errors)

    def test_hu02_rechaza_confirmacion_distinta(self):
        form = RegistroForm({**DATOS_VALIDOS, "password2": "Otra2026x"})
        self.assertFalse(form.is_valid())
        self.assertIn("password2", form.errors)

    def test_hu02_registro_no_permite_elegir_rol(self):
        Rol.objects.create(nombre_rol="Administrador")
        self.client.post(reverse("usuarios:registro"), {**DATOS_VALIDOS, "rol": 99})
        self.assertEqual(Usuario.objects.get(correo="cecilia@correo.com").nombre_rol, "estudiante")


class LoginTests(TestCase):
    def test_hu01_login_correcto_redirige_al_panel(self):
        crear_usuario()
        respuesta = self.client.post(
            reverse("usuarios:login"), {"correo": "ANA@correo.com", "password": "clave1234"}
        )
        self.assertRedirects(respuesta, reverse("usuarios:panel_estudiante"))

    def test_hu01_login_incorrecto_muestra_error(self):
        crear_usuario()
        respuesta = self.client.post(
            reverse("usuarios:login"), {"correo": "ana@correo.com", "password": "mala1234"}
        )
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")


class RecuperacionTests(TestCase):
    def setUp(self):
        self.usuario = crear_usuario()

    def _solicitar(self):
        return services.solicitar_recuperacion(self.usuario.correo, lambda ruta: f"http://test{ruta}")

    def test_hu12_token_expira_en_30_minutos_y_se_guarda_hasheado(self):
        token = self._solicitar()
        registro = TokenRecuperacion.objects.get(usuario=self.usuario)
        self.assertNotEqual(registro.token_hash, token)
        duracion = registro.fecha_expiracion - registro.fecha_creacion
        self.assertAlmostEqual(duracion.total_seconds(), 30 * 60, delta=5)

    def test_hu12_token_expirado_no_permite_restablecer(self):
        token = self._solicitar()
        ahora = timezone.now()
        TokenRecuperacion.objects.filter(usuario=self.usuario).update(
            fecha_creacion=ahora - timedelta(hours=1),
            fecha_expiracion=ahora - timedelta(minutes=1),
        )
        self.assertIsNone(services.obtener_token_vigente(token))
        self.assertFalse(services.restablecer_contrasena(token, "Nueva2026"))
        self.usuario.refresh_from_db()
        self.assertTrue(self.usuario.check_password("clave1234"))

    def test_hu12_token_es_de_un_solo_uso(self):
        token = self._solicitar()
        self.assertTrue(services.restablecer_contrasena(token, "Nueva2026"))
        self.assertFalse(services.restablecer_contrasena(token, "Otra2026x"))

    def test_hu12_nuevo_token_invalida_el_anterior(self):
        primero = self._solicitar()
        self._solicitar()
        self.assertIsNone(services.obtener_token_vigente(primero))

    def test_hu12_correo_inexistente_no_crea_token(self):
        resultado = services.solicitar_recuperacion("nadie@correo.com", lambda r: r)
        self.assertIsNone(resultado)
        self.assertFalse(TokenRecuperacion.objects.exists())


class GestionUsuariosTests(TestCase):
    def setUp(self):
        rol_admin = Rol.objects.create(nombre_rol="Administrador")
        self.rol_profesor = Rol.objects.create(nombre_rol="Profesor")
        self.admin = Usuario.objects.create_user(
            "admin@correo.com", "admin1234", nombre="Lolo", apellido="Admin", rol=rol_admin
        )
        self.estudiante = crear_usuario("est@correo.com")
        self.client.force_login(self.admin)

    def test_hu09_admin_ve_la_lista_de_usuarios(self):
        respuesta = self.client.get(reverse("usuarios:gestion_usuarios"))
        self.assertContains(respuesta, "est@correo.com")

    def test_hu09_estudiante_no_puede_entrar_a_gestion(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(reverse("usuarios:gestion_usuarios")).status_code, 403)

    def test_hu09_borrado_logico_desactiva_y_bloquea_login(self):
        self.client.post(reverse("usuarios:gestion_usuario_estado", args=[self.estudiante.pk]))
        self.estudiante.refresh_from_db()
        self.assertFalse(self.estudiante.estado)
        self.assertTrue(Usuario.objects.filter(pk=self.estudiante.pk).exists())
        self.client.logout()
        respuesta = self.client.post(
            reverse("usuarios:login"), {"correo": "est@correo.com", "password": "clave1234"}
        )
        self.assertContains(respuesta, "Correo o contraseña incorrectos.")

    def test_hu09_admin_no_puede_desactivarse_a_si_mismo(self):
        self.client.post(reverse("usuarios:gestion_usuario_estado", args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.estado)

    def test_hu09_editar_cambia_rol_y_rechaza_correo_repetido(self):
        url = reverse("usuarios:gestion_usuario_editar", args=[self.estudiante.pk])
        datos = {"nombre": "Ana", "apellido": "Pérez", "correo": "admin@correo.com",
                 "rol": self.rol_profesor.pk, "estado": "on"}
        self.assertEqual(self.client.post(url, datos).status_code, 200)
        datos["correo"] = "est@correo.com"
        self.assertEqual(self.client.post(url, datos).status_code, 302)
        self.estudiante.refresh_from_db()
        self.assertEqual(self.estudiante.nombre_rol, "profesor")

    def test_hu09_crear_profesor_desde_el_panel(self):
        self.client.post(reverse("usuarios:gestion_usuario_nuevo"), {
            "nombre": "Georgina", "apellido": "Aruquipa", "correo": "profe@correo.com",
            "rol": self.rol_profesor.pk, "password1": "Profe2026", "password2": "Profe2026",
        })
        profe = Usuario.objects.get(correo="profe@correo.com")
        self.assertEqual(profe.nombre_rol, "profesor")
        self.assertTrue(EstadisticasUsuario.objects.filter(usuario=profe).exists())