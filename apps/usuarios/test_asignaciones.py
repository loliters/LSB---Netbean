"""Pruebas de la relación profesor–estudiante y de la asignación de contenido (HU-13)."""
import json
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from apps.contenido import services as contenido_services
from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, Rol, TipoSena
from apps.gamificacion.services import registrar_intento
from apps.progreso.models import Practica, ProgresoSena
from apps.usuarios import asignaciones
from apps.usuarios.models import AsignacionContenido, AsignacionProfesor, Usuario

CLAVE = "clave1234"


def crear(correo: str, nombre_rol: str, nombre: str) -> Usuario:
    rol, _ = Rol.objects.get_or_create(nombre_rol=nombre_rol)
    return Usuario.objects.create_user(correo, CLAVE, nombre=nombre, apellido="Prueba", rol=rol)


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear("admin@correo.com", "Administrador", "Admin")
        cls.profe = crear("profe@correo.com", "Profesor", "Profe")
        cls.otro_profe = crear("otro@correo.com", "Profesor", "Otro")
        cls.ana = crear("ana@correo.com", "Estudiante", "Ana")
        cls.beto = crear("beto@correo.com", "Estudiante", "Beto")
        cls.carla = crear("carla@correo.com", "Estudiante", "Carla")
        dificultad = Dificultad.objects.create(nivel=1, nombre="Básico", multiplicador_xp=Decimal("1.00"))
        tipo = TipoSena.objects.create(nombre="Estática")
        categoria = Categoria.objects.create(nombre="Alfabeto")
        cls.m1 = Modulo.objects.create(categoria=categoria, nombre="Vocales", orden=1)
        cls.m2 = Modulo.objects.create(categoria=categoria, nombre="Números", orden=2)
        cls.l1 = Leccion.objects.create(modulo=cls.m1, nombre="Abiertas", orden=1)
        cls.l1b = Leccion.objects.create(modulo=cls.m1, nombre="Cerradas", orden=2)
        cls.l2 = Leccion.objects.create(modulo=cls.m2, nombre="Uno a tres", orden=1)

        def sena(leccion, nombre):
            return Sena.objects.create(leccion=leccion, tipo_sena=tipo, dificultad=dificultad,
                                       nombre=nombre, ruta_imagen=f"senas/{nombre.lower()}.png")

        cls.sA, cls.sE, cls.sI, cls.s1 = sena(cls.l1, "A"), sena(cls.l1, "E"), sena(cls.l1b, "I"), sena(cls.l2, "1")

    def entrar(self, usuario):
        self.client.force_login(usuario)

    def asignar(self, profesor, *estudiantes):
        return asignaciones.asignar_estudiantes(profesor, [e.pk for e in estudiantes])


class ProfesorEstudiantesTests(Base):
    def test_profesor_se_asigna_estudiantes(self):
        self.entrar(self.profe)
        self.client.post(reverse("usuarios:profesor_estudiantes"),
                         {"estudiantes": [self.ana.pk, self.beto.pk], "accion": "asignar"})
        self.assertEqual({e.pk for e in asignaciones.mis_estudiantes(self.profe)}, {self.ana.pk, self.beto.pk})

    def test_solo_se_pueden_asignar_estudiantes(self):
        self.entrar(self.profe)
        self.client.post(reverse("usuarios:profesor_estudiantes"),
                         {"estudiantes": [self.admin.pk, self.otro_profe.pk, self.ana.pk], "accion": "asignar"})
        self.assertEqual(list(AsignacionProfesor.objects.values_list("estudiante_id", flat=True)), [self.ana.pk])

    def test_asignar_dos_veces_no_duplica(self):
        self.asignar(self.profe, self.ana)
        self.assertEqual(self.asignar(self.profe, self.ana), 0)
        self.assertEqual(AsignacionProfesor.objects.filter(profesor=self.profe, estudiante=self.ana).count(), 1)

    def test_quitar_desactiva_y_devuelve_el_catalogo_completo(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m1.pk)
        self.assertIsNotNone(asignaciones.alcance_contenido(self.ana))
        self.entrar(self.profe)
        self.client.post(reverse("usuarios:profesor_estudiantes"), {"estudiantes": [self.ana.pk], "accion": "quitar"})
        self.assertFalse(AsignacionProfesor.objects.get(profesor=self.profe, estudiante=self.ana).activo)
        self.assertFalse(AsignacionContenido.objects.filter(estudiante=self.ana, activo=True).exists())
        self.assertIsNone(asignaciones.alcance_contenido(self.ana))

    def test_un_estudiante_puede_tener_varios_profesores(self):
        self.asignar(self.profe, self.ana)
        self.asignar(self.otro_profe, self.ana)
        self.assertEqual(asignaciones.mis_estudiantes(self.otro_profe).count(), 1)

    def test_la_lista_muestra_quien_monitorea_a_cada_estudiante(self):
        self.asignar(self.otro_profe, self.carla)
        self.entrar(self.profe)
        respuesta = self.client.get(reverse("usuarios:profesor_estudiantes"))
        self.assertContains(respuesta, "Con Otro Prueba")
        self.assertContains(respuesta, "Sin profesor")

    def test_la_lista_no_incluye_administradores_ni_profesores(self):
        self.entrar(self.profe)
        respuesta = self.client.get(reverse("usuarios:profesor_estudiantes"))
        self.assertContains(respuesta, "ana@correo.com")
        self.assertNotContains(respuesta, "admin@correo.com")
        self.assertNotContains(respuesta, "otro@correo.com")

    def test_estudiante_y_administrador_no_acceden(self):
        for usuario in (self.ana, self.admin):
            self.entrar(usuario)
            self.assertEqual(self.client.get(reverse("usuarios:profesor_estudiantes")).status_code, 403)
            self.assertEqual(self.client.get(reverse("usuarios:profesor_contenido")).status_code, 403)


class AsignarContenidoTests(Base):
    def setUp(self):
        self.asignar(self.profe, self.ana)
        self.entrar(self.profe)
        self.url = reverse("usuarios:profesor_contenido")

    def test_profesor_asigna_un_modulo_a_su_estudiante(self):
        respuesta = self.client.post(self.url, {"estudiantes": [self.ana.pk], "objetivo": f"m:{self.m1.pk}"})
        self.assertRedirects(respuesta, self.url)
        self.assertTrue(AsignacionContenido.objects.filter(estudiante=self.ana, modulo=self.m1, activo=True).exists())

    def test_no_puede_asignar_a_un_estudiante_ajeno(self):
        respuesta = self.client.post(self.url, {"estudiantes": [self.beto.pk], "objetivo": f"m:{self.m1.pk}"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(AsignacionContenido.objects.exists())

    def test_objetivo_invalido_no_asigna_nada(self):
        for valor in ("x:1", "m:", "m:999", "", "sena"):
            self.client.post(self.url, {"estudiantes": [self.ana.pk], "objetivo": valor})
        self.assertFalse(AsignacionContenido.objects.exists())

    def test_no_se_asigna_contenido_inactivo(self):
        self.m2.estado = False
        self.m2.save()
        self.client.post(self.url, {"estudiantes": [self.ana.pk], "objetivo": f"m:{self.m2.pk}"})
        self.assertFalse(AsignacionContenido.objects.exists())

    def test_asignar_dos_veces_no_duplica(self):
        datos = {"estudiantes": [self.ana.pk], "objetivo": f"l:{self.l1.pk}"}
        self.client.post(self.url, datos)
        self.client.post(self.url, datos)
        self.assertEqual(AsignacionContenido.objects.filter(estudiante=self.ana, leccion=self.l1).count(), 1)

    def test_solo_el_profesor_dueno_puede_quitar_una_asignacion(self):
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "sena", self.sA.pk)
        asignacion = AsignacionContenido.objects.get()
        self.entrar(self.otro_profe)
        self.client.post(reverse("usuarios:profesor_contenido_quitar", args=[asignacion.pk]))
        asignacion.refresh_from_db()
        self.assertTrue(asignacion.activo)
        self.entrar(self.profe)
        self.client.post(reverse("usuarios:profesor_contenido_quitar", args=[asignacion.pk]))
        asignacion.refresh_from_db()
        self.assertFalse(asignacion.activo)

    def test_la_base_de_datos_exige_un_unico_objetivo(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsignacionContenido.objects.create(profesor=self.profe, estudiante=self.ana, modulo=self.m1, leccion=self.l1)
        with self.assertRaises(IntegrityError), transaction.atomic():
            AsignacionContenido.objects.create(profesor=self.profe, estudiante=self.ana)


class ContenidoVisibleTests(Base):
    def _modulos(self):
        return {m.nombre: m for m in contenido_services.listar_modulos_con_progreso(self.ana)}

    def test_sin_asignaciones_el_estudiante_ve_todo(self):
        modulos = self._modulos()
        self.assertEqual(set(modulos), {"Vocales", "Números"})
        self.assertEqual(modulos["Vocales"].total_senas, 3)

    def test_con_un_modulo_asignado_solo_ve_ese_modulo(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m2.pk)
        self.assertEqual(set(self._modulos()), {"Números"})
        modulo, _ = contenido_services.detalle_modulo(self.m1.pk, self.ana)
        self.assertIsNone(modulo)

    def test_con_una_leccion_asignada_el_modulo_muestra_solo_esa_leccion(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "leccion", self.l1b.pk)
        modulos = self._modulos()
        self.assertEqual(set(modulos), {"Vocales"})
        self.assertEqual((modulos["Vocales"].total_lecciones, modulos["Vocales"].total_senas), (1, 1))
        modulo, _ = contenido_services.detalle_modulo(self.m1.pk, self.ana)
        self.assertEqual([le.nombre for le in modulo.lecciones_activas], ["Cerradas"])

    def test_con_una_sena_asignada_solo_ve_esa_sena(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "sena", self.sA.pk)
        modulo, _ = contenido_services.detalle_modulo(self.m1.pk, self.ana)
        nombres = [s.nombre for le in modulo.lecciones_activas for s in le.senas.all()]
        self.assertEqual(nombres, ["A"])

    def test_dos_profesores_suman_sus_asignaciones(self):
        self.asignar(self.profe, self.ana)
        self.asignar(self.otro_profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m1.pk)
        asignaciones.asignar_contenido(self.otro_profe, [self.ana.pk], "modulo", self.m2.pk)
        self.assertEqual(set(self._modulos()), {"Vocales", "Números"})

    def test_el_porcentaje_cuenta_solo_lo_asignado(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "leccion", self.l1b.pk)
        ProgresoSena.objects.create(usuario=self.ana, sena=self.sI, dominada=True)
        ProgresoSena.objects.create(usuario=self.ana, sena=self.sA, dominada=True)  # no asignada: no cuenta
        self.assertEqual(self._modulos()["Vocales"].porcentaje, 100)

    def test_la_leccion_se_completa_con_las_senas_asignadas(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "sena", self.sA.pk)
        resultado = registrar_intento(usuario=self.ana, sena=self.sA, letra_predicha="A", confianza=0.95)
        self.assertEqual(resultado["total_senas"], 1)
        self.assertTrue(resultado["leccion_completada"])

    def test_practica_de_una_sena_no_asignada_responde_404(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "leccion", self.l1b.pk)
        self.entrar(self.ana)
        self.assertEqual(self.client.get(reverse("reconocimiento:practica", args=[self.s1.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("reconocimiento:practica", args=[self.sA.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse("reconocimiento:practica", args=[self.sI.pk])).status_code, 200)

    def test_evaluar_una_sena_no_asignada_responde_404(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m2.pk)
        self.entrar(self.ana)
        cuerpo = {"id_sena": self.sA.pk, "id_leccion": self.l1.pk, "frame": "x"}
        respuesta = self.client.post(reverse("gamificacion:evaluar"), json.dumps(cuerpo), content_type="application/json")
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Practica.objects.exists())

    def test_continuar_abre_una_sena_asignada(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "sena", self.sI.pk)
        self.entrar(self.ana)
        respuesta = self.client.get(reverse("reconocimiento:continuar"))
        self.assertRedirects(respuesta, reverse("reconocimiento:practica", args=[self.sI.pk]))

    def test_el_catalogo_avisa_que_hay_contenido_asignado(self):
        self.entrar(self.ana)
        self.assertNotContains(self.client.get(reverse("contenido:mapa_modulos")), "tu profesor te asignó")
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m1.pk)
        self.assertContains(self.client.get(reverse("contenido:mapa_modulos")), "tu profesor te asignó")

    def test_el_profesor_y_el_administrador_ven_todo_el_catalogo(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m1.pk)
        self.assertIsNone(asignaciones.alcance_contenido(self.profe))
        self.assertIsNone(asignaciones.alcance_contenido(self.admin))


class AdminProfesoresTests(Base):
    def setUp(self):
        self.entrar(self.admin)

    def test_el_administrador_lista_a_los_profesores(self):
        self.asignar(self.profe, self.ana)
        respuesta = self.client.get(reverse("usuarios:gestion_profesores"))
        self.assertContains(respuesta, "profe@correo.com")
        self.assertContains(respuesta, "otro@correo.com")
        self.assertNotContains(respuesta, "ana@correo.com")

    def test_el_administrador_asigna_y_quita_estudiantes(self):
        url = reverse("usuarios:gestion_profesor_detalle", args=[self.profe.pk])
        self.client.post(url, {"estudiantes": [self.ana.pk, self.beto.pk]})
        self.assertEqual({e.pk for e in asignaciones.mis_estudiantes(self.profe)}, {self.ana.pk, self.beto.pk})
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "modulo", self.m1.pk)
        self.client.post(url, {"estudiantes": [self.beto.pk]})
        self.assertEqual({e.pk for e in asignaciones.mis_estudiantes(self.profe)}, {self.beto.pk})
        self.assertFalse(AsignacionContenido.objects.filter(estudiante=self.ana, activo=True).exists())

    def test_la_asignacion_registra_quien_la_hizo(self):
        self.client.post(reverse("usuarios:gestion_profesor_detalle", args=[self.profe.pk]), {"estudiantes": [self.ana.pk]})
        self.assertEqual(AsignacionProfesor.objects.get().asignado_por, self.admin)

    def test_ignora_ids_que_no_son_estudiantes(self):
        url = reverse("usuarios:gestion_profesor_detalle", args=[self.profe.pk])
        self.client.post(url, {"estudiantes": [self.admin.pk, self.otro_profe.pk]})
        self.assertFalse(AsignacionProfesor.objects.exists())

    def test_el_detalle_solo_existe_para_profesores(self):
        self.assertEqual(self.client.get(reverse("usuarios:gestion_profesor_detalle", args=[self.ana.pk])).status_code, 404)

    def test_profesor_y_estudiante_no_acceden(self):
        for usuario in (self.profe, self.ana):
            self.entrar(usuario)
            self.assertEqual(self.client.get(reverse("usuarios:gestion_profesores")).status_code, 403)
            self.assertEqual(
                self.client.get(reverse("usuarios:gestion_profesor_detalle", args=[self.profe.pk])).status_code, 403)


class PanelYNavegacionTests(Base):
    def test_el_panel_muestra_avance_y_estudiantes_sin_actividad(self):
        self.asignar(self.profe, self.ana, self.beto)
        Practica.objects.create(usuario=self.ana, sena=self.sA, numero_intento=1, puntaje_obtenido=Decimal("90"),
                                xp_ganado=30, es_correcta=True)
        self.entrar(self.profe)
        respuesta = self.client.get(reverse("usuarios:panel_profesor"))
        self.assertContains(respuesta, "Ana Prueba")
        self.assertContains(respuesta, "Beto Prueba")
        self.assertContains(respuesta, "Sin actividad")
        self.assertNotContains(respuesta, "Carla Prueba")

    def test_el_panel_sin_estudiantes_invita_a_elegirlos(self):
        self.entrar(self.profe)
        self.assertContains(self.client.get(reverse("usuarios:panel_profesor")), "Aún no monitoreas")

    def test_avance_cuenta_solo_lo_asignado(self):
        self.asignar(self.profe, self.ana)
        asignaciones.asignar_contenido(self.profe, [self.ana.pk], "leccion", self.l1b.pk)
        ProgresoSena.objects.create(usuario=self.ana, sena=self.sI, dominada=True)
        fila = asignaciones.avance_estudiantes(self.profe)[0]
        self.assertEqual((fila["dominadas"], fila["total"], fila["porcentaje"]), (1, 1, 100))

    def test_la_navegacion_muestra_enlaces_segun_el_rol(self):
        self.entrar(self.profe)
        html = self.client.get(reverse("usuarios:panel_profesor")).content.decode()
        self.assertIn("Mis estudiantes", html)
        self.assertNotIn(reverse("usuarios:gestion_profesores"), html)
        self.entrar(self.admin)
        html = self.client.get(reverse("usuarios:panel_admin")).content.decode()
        self.assertIn(reverse("usuarios:gestion_profesores"), html)
        self.assertNotIn(reverse("usuarios:profesor_estudiantes"), html)
        self.entrar(self.ana)
        html = self.client.get(reverse("usuarios:panel_estudiante")).content.decode()
        self.assertNotIn(reverse("usuarios:profesor_estudiantes"), html)
