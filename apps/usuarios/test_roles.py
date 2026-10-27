"""Pruebas de roles: administrador y profesor no tienen nada de estudiante."""
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.core.models import Rol
from apps.gamificacion.models import UsuarioLogro
from apps.usuarios.models import EstadisticasUsuario, Usuario

CLAVE = "clave1234"


def crear(correo: str, rol: Rol, nombre: str = "Persona") -> Usuario:
    return Usuario.objects.create_user(correo, CLAVE, nombre=nombre, apellido="Prueba", rol=rol)


class RolesBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear("admin@correo.com", Rol.objects.create(nombre_rol="Administrador"), "Admin")
        cls.profesor = crear("profe@correo.com", Rol.objects.create(nombre_rol="Profesor"), "Profe")
        cls.estudiante = crear("ana@correo.com", Rol.objects.create(nombre_rol="Estudiante"), "Ana")


class PerfilPorRolTests(RolesBase):
    def _perfil(self, usuario):
        self.client.force_login(usuario)
        return self.client.get(reverse("usuarios:perfil"))

    def test_admin_y_profesor_ven_perfil_de_cuenta_sin_gamificacion(self):
        for usuario in (self.admin, self.profesor):
            respuesta = self._perfil(usuario)
            self.assertEqual(respuesta.status_code, 200)
            self.assertTemplateUsed(respuesta, "usuarios/perfil_cuenta.html")
            for texto in ("XP total", "Racha", "Insignias", "Nivel"):
                self.assertNotContains(respuesta, texto)
            self.assertContains(respuesta, "Cambiar contraseña")

    def test_estudiante_sigue_viendo_su_perfil_gamificado(self):
        respuesta = self._perfil(self.estudiante)
        self.assertTemplateUsed(respuesta, "usuarios/perfil.html")
        self.assertContains(respuesta, "XP total")

    def test_ver_perfil_no_crea_estadisticas_de_admin_ni_profesor(self):
        self._perfil(self.admin)
        self._perfil(self.profesor)
        self.assertFalse(EstadisticasUsuario.objects.filter(usuario__in=[self.admin, self.profesor]).exists())


class CambiarContrasenaTests(RolesBase):
    def test_cambia_la_contrasena_y_mantiene_la_sesion(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse("usuarios:perfil"), {
            "actual": CLAVE, "password1": "Zorro7391Azul", "password2": "Zorro7391Azul",
        })
        self.assertRedirects(respuesta, reverse("usuarios:perfil"))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password("Zorro7391Azul"))
        self.assertEqual(self.client.get(reverse("usuarios:perfil")).status_code, 200)

    def test_rechaza_contrasena_actual_incorrecta(self):
        self.client.force_login(self.profesor)
        respuesta = self.client.post(reverse("usuarios:perfil"), {
            "actual": "incorrecta1", "password1": "Zorro7391Azul", "password2": "Zorro7391Azul",
        })
        self.assertContains(respuesta, "La contraseña actual no es correcta.")
        self.profesor.refresh_from_db()
        self.assertTrue(self.profesor.check_password(CLAVE))

    def test_rechaza_si_la_nueva_no_coincide(self):
        self.client.force_login(self.admin)
        respuesta = self.client.post(reverse("usuarios:perfil"), {
            "actual": CLAVE, "password1": "Zorro7391Azul", "password2": "Otra7391Azul",
        })
        self.assertContains(respuesta, "Las contraseñas no coinciden.")


class AccesoSoloEstudianteTests(RolesBase):
    def test_admin_y_profesor_no_acceden_a_practica_ni_logros(self):
        urls = [reverse("gamificacion:logros"), reverse("gamificacion:progreso"), reverse("reconocimiento:continuar")]
        for usuario in (self.admin, self.profesor):
            self.client.force_login(usuario)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403, f"{usuario.nombre_rol} → {url}")

    def test_admin_y_profesor_no_pueden_evaluar_ni_predecir(self):
        for usuario in (self.admin, self.profesor):
            self.client.force_login(usuario)
            for nombre in ("gamificacion:evaluar", "reconocimiento:predecir"):
                self.assertEqual(self.client.post(reverse(nombre), {}, content_type="application/json").status_code, 403)

    def test_estudiante_si_accede_a_logros(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(reverse("gamificacion:logros")).status_code, 200)


class LimpiarEstadisticasStaffTests(RolesBase):
    def test_comando_borra_estadisticas_de_no_estudiantes(self):
        for usuario in (self.admin, self.profesor, self.estudiante):
            EstadisticasUsuario.objects.create(usuario=usuario)
        call_command("limpiar_estadisticas_staff", verbosity=0)
        self.assertEqual(list(EstadisticasUsuario.objects.values_list("usuario_id", flat=True)), [self.estudiante.pk])
        self.assertFalse(UsuarioLogro.objects.filter(usuario__in=[self.admin, self.profesor]).exists())
