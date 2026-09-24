"""Pruebas de la app usuarios (HU-01, HU-02)."""
from django.test import TestCase
from django.urls import reverse

from .models import Usuario


class UsuarioModelTests(TestCase):
    """Pruebas del modelo Usuario."""

    def test_hu01_ca1_correo_unico(self):
        """CA1: el correo electrónico debe ser único."""
        Usuario.objects.create_user(
            username='usuario1',
            correo='correo@lsb.bo',
            password='test1234',
        )
        with self.assertRaises(Exception):
            Usuario.objects.create_user(
                username='usuario2',
                correo='correo@lsb.bo',
                password='test1234',
            )

    def test_hu02_ca3_rol_por_defecto_es_estudiante(self):
        """CA3: al registrar se asigna rol Estudiante."""
        usuario = Usuario.objects.create_user(
            username='estudiante1',
            correo='est@lsb.bo',
            password='test1234',
        )
        self.assertEqual(usuario.rol, Usuario.Rol.ESTUDIANTE)
        self.assertTrue(usuario.es_estudiante)

    def test_password_hasheada(self):
        """La contraseña se guarda hasheada, nunca en texto plano."""
        usuario = Usuario.objects.create_user(
            username='user_hash',
            correo='hash@lsb.bo',
            password='mi_password_segura',
        )
        self.assertNotEqual(usuario.password, 'mi_password_segura')
        self.assertTrue(usuario.check_password('mi_password_segura'))


class LoginViewTests(TestCase):
    """Pruebas de la vista de login (HU-01)."""

    def setUp(self):
        self.usuario = Usuario.objects.create_user(
            username='estu_login',
            correo='estu_login@lsb.bo',
            password='clave123',
        )

    def test_hu01_ca1_login_con_credenciales_validas(self):
        """CA1: login correcto redirige al panel del estudiante."""
        respuesta = self.client.post(reverse('usuarios:login'), {
            'identificador': 'estu_login',
            'password': 'clave123',
        })
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/panel/estudiante/', respuesta.url)

    def test_hu01_ca2_login_con_password_incorrecta(self):
        """CA2: login con password incorrecta no autentica."""
        respuesta = self.client.post(reverse('usuarios:login'), {
            'identificador': 'estu_login',
            'password': 'clave_incorrecta',
        })
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Credenciales inválidas')

    def test_hu01_login_con_correo(self):
        """Login alternativo usando correo electrónico."""
        respuesta = self.client.post(reverse('usuarios:login'), {
            'identificador': 'estu_login@lsb.bo',
            'password': 'clave123',
        })
        self.assertEqual(respuesta.status_code, 302)

    def test_hu01_ca3_logout_redirige_a_login(self):
        """CA3: logout limpia la sesión y redirige al login."""
        self.client.login(username='estu_login', password='clave123')
        respuesta = self.client.post(reverse('usuarios:logout'))
        self.assertEqual(respuesta.status_code, 302)
        self.assertIn('/usuarios/login/', respuesta.url)


class RegistroViewTests(TestCase):
    """Pruebas de la vista de registro (HU-02)."""

    def test_hu02_registro_crea_estudiante(self):
        """CA1-CA4: registro crea usuario con rol Estudiante."""
        respuesta = self.client.post(reverse('usuarios:registro'), {
            'username': 'nuevo_estu',
            'correo': 'nuevo@lsb.bo',
            'password1': 'ClaveSegura123!',
            'password2': 'ClaveSegura123!',
        })
        self.assertEqual(respuesta.status_code, 302)
        usuario = Usuario.objects.get(username='nuevo_estu')
        self.assertEqual(usuario.rol, Usuario.Rol.ESTUDIANTE)


class PanelEstudianteTests(TestCase):
    """Pruebas de acceso al panel del estudiante."""

    def test_panel_requiere_login(self):
        """Sin login no se puede acceder al panel."""
        respuesta = self.client.get(reverse('usuarios:panel_estudiante'))
        self.assertEqual(respuesta.status_code, 302)

    def test_panel_rechaza_a_profesor(self):
        """Un profesor no puede acceder al panel del estudiante."""
        Usuario.objects.create_user(
            username='profe_test',
            correo='profe_test@lsb.bo',
            password='clave123',
            rol='PROFESOR',
        )
        self.client.login(username='profe_test', password='clave123')
        respuesta = self.client.get(reverse('usuarios:panel_estudiante'))
        self.assertEqual(respuesta.status_code, 403)