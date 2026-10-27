"""El profesor ve reportes solo de sus estudiantes; el administrador, de todos (HU-13, HU-10)."""
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from openpyxl import load_workbook

from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, Rol, TipoSena
from apps.progreso.models import Practica
from apps.usuarios import asignaciones
from apps.usuarios.models import Usuario

from . import services
from .forms import FiltroReporteForm


def crear(correo: str, nombre_rol: str, nombre: str, apellido: str = "Prueba") -> Usuario:
    rol, _ = Rol.objects.get_or_create(nombre_rol=nombre_rol)
    return Usuario.objects.create_user(correo, "clave1234", nombre=nombre, apellido=apellido, rol=rol)


class AlcanceBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = crear("admin@correo.com", "Administrador", "Admin")
        cls.profe = crear("profe@correo.com", "Profesor", "Profe")
        cls.profe_vacio = crear("vacio@correo.com", "Profesor", "Vacio")
        cls.ana = crear("ana@correo.com", "Estudiante", "Ana")
        cls.beto = crear("beto@correo.com", "Estudiante", "Beto")
        cls.zoila = crear("zoila@correo.com", "Estudiante", "Zoila", "Tercera")   # no es de la profesora
        dificultad = Dificultad.objects.create(nivel=1, nombre="Básico", multiplicador_xp=Decimal("1"))
        modulo = Modulo.objects.create(categoria=Categoria.objects.create(nombre="Alfabeto"), nombre="Vocales", orden=1)
        leccion = Leccion.objects.create(modulo=modulo, nombre="Abiertas", orden=1)
        sena = Sena.objects.create(leccion=leccion, tipo_sena=TipoSena.objects.create(nombre="Estática"),
                                   dificultad=dificultad, nombre="A", ruta_imagen="senas/a.png")
        asignaciones.asignar_estudiantes(cls.profe, [cls.ana.pk, cls.beto.pk])
        # Ana: 2 intentos (1 acierto). Zoila: 3 intentos. Beto: ninguno.
        for numero, correcta in enumerate([True, False], start=1):
            cls._practica(cls.ana, sena, numero, correcta)
        for numero in range(1, 4):
            cls._practica(cls.zoila, sena, numero, True)

    @staticmethod
    def _practica(usuario, sena, numero, correcta):
        Practica.objects.create(usuario=usuario, sena=sena, numero_intento=numero, es_correcta=correcta,
                                puntaje_obtenido=Decimal("90" if correcta else "40"), xp_ganado=30 if correcta else 0)


class AlcanceServiciosTests(AlcanceBase):
    def test_el_profesor_solo_cuenta_a_sus_estudiantes(self):
        filtros = FiltroReporteForm(usuario=self.profe).filtros()
        resumen = services.resumen(filtros)
        self.assertEqual(resumen["intentos"], 2)
        self.assertEqual(resumen["estudiantes_registrados"], 2)
        self.assertEqual([f["correo"] for f in services.por_estudiante(filtros)], ["ana@correo.com"])

    def test_el_administrador_ve_a_todos(self):
        filtros = FiltroReporteForm(usuario=self.admin).filtros()
        self.assertEqual(services.resumen(filtros)["intentos"], 5)
        self.assertEqual(services.resumen(filtros)["estudiantes_registrados"], 3)

    def test_un_profesor_sin_estudiantes_no_ve_datos(self):
        filtros = FiltroReporteForm(usuario=self.profe_vacio).filtros()
        self.assertEqual(services.resumen(filtros)["intentos"], 0)
        self.assertEqual(services.por_estudiante(filtros), [])

    def test_sin_actividad_lista_a_quien_no_practico(self):
        filtros = FiltroReporteForm(usuario=self.profe).filtros()
        self.assertEqual([e["nombre"] for e in services.sin_actividad(filtros)], ["Beto Prueba"])

    def test_el_estudiante_elegido_acota_el_reporte(self):
        form = FiltroReporteForm({**FiltroReporteForm.valores_iniciales(), "estudiante": self.ana.pk}, usuario=self.profe)
        filtros = form.filtros()
        self.assertEqual(filtros.estudiante, self.ana)
        self.assertEqual(services.resumen(filtros)["intentos"], 2)
        self.assertIn("Estudiante: Ana", filtros.descripcion)

    def test_el_formulario_del_profesor_rechaza_a_un_estudiante_ajeno(self):
        datos = {**FiltroReporteForm.valores_iniciales(), "estudiante": self.zoila.pk}
        self.assertFalse(FiltroReporteForm(datos, usuario=self.profe).is_valid())

    def test_un_formulario_invalido_no_amplia_el_alcance(self):
        datos = {"desde": "2026-10-20", "hasta": "2026-10-01"}
        filtros = FiltroReporteForm(datos, usuario=self.profe).filtros()
        self.assertEqual(services.resumen(filtros)["intentos"], 2)

    def test_las_opciones_de_estudiante_del_profesor_son_solo_las_suyas(self):
        opciones = set(FiltroReporteForm(usuario=self.profe).fields["estudiante"].queryset.values_list("pk", flat=True))
        self.assertEqual(opciones, {self.ana.pk, self.beto.pk})


class AlcanceVistasTests(AlcanceBase):
    def setUp(self):
        self.client.force_login(self.profe)
        self.url = reverse("reportes:dashboard")

    def test_el_dashboard_del_profesor_no_muestra_estudiantes_ajenos(self):
        respuesta = self.client.get(self.url)
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ana Prueba")
        self.assertNotContains(respuesta, "Zoila")
        self.assertContains(respuesta, "Solo tus estudiantes")

    def test_pedir_a_un_estudiante_ajeno_responde_403_en_pantalla_y_exportaciones(self):
        for nombre in ("reportes:dashboard", "reportes:exportar_excel", "reportes:exportar_pdf"):
            self.assertEqual(self.client.get(reverse(nombre), {"estudiante": self.zoila.pk}).status_code, 403)

    def test_un_identificador_que_no_es_numero_responde_403(self):
        self.assertEqual(self.client.get(self.url, {"estudiante": "abc"}).status_code, 403)
        self.assertEqual(self.client.get(self.url, {"estudiante": "999999"}).status_code, 403)

    def test_pedir_a_un_estudiante_propio_filtra_el_reporte(self):
        respuesta = self.client.get(self.url, {"estudiante": self.ana.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Estudiante: Ana")

    def test_un_enlace_solo_con_estudiante_conserva_el_filtro(self):
        respuesta = self.client.get(self.url, {"estudiante": self.beto.pk})
        self.assertContains(respuesta, "Estudiante: Beto")

    def test_un_formulario_invalido_sigue_sin_mostrar_ajenos(self):
        respuesta = self.client.get(self.url, {"desde": "2026-10-20", "hasta": "2026-10-01"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotContains(respuesta, "Zoila")

    def test_el_excel_del_profesor_solo_trae_a_sus_estudiantes(self):
        respuesta = self.client.get(reverse("reportes:exportar_excel"))
        self.assertEqual(respuesta.status_code, 200)
        hoja = load_workbook(BytesIO(respuesta.content))["Por estudiante"]
        nombres = [fila[0] for fila in hoja.iter_rows(min_row=2, values_only=True) if fila[0]]
        self.assertEqual(nombres, ["Ana Prueba"])

    def test_el_pdf_del_profesor_se_genera(self):
        respuesta = self.client.get(reverse("reportes:exportar_pdf"))
        self.assertEqual(respuesta["Content-Type"], "application/pdf")

    def test_el_profesor_sin_estudiantes_ve_un_aviso(self):
        self.client.force_login(self.profe_vacio)
        self.assertContains(self.client.get(self.url), "Aún no monitoreas")

    def test_el_administrador_puede_filtrar_por_cualquier_estudiante(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(self.url, {"estudiante": self.zoila.pk})
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Estudiante: Zoila")
        self.assertNotContains(respuesta, "Solo tus estudiantes")

    def test_el_estudiante_no_accede_a_reportes(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(self.url).status_code, 403)
