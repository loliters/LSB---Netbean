"""Pruebas del reporte de progreso (HU-10)."""
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from openpyxl import load_workbook

from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, Rol, TipoSena
from apps.progreso.models import Practica
from apps.usuarios.models import Usuario

from . import services
from .forms import FiltroReporteForm


class ReporteBase(TestCase):
    def setUp(self):
        self.rol_est = Rol.objects.create(nombre_rol="Estudiante")
        self.admin = Usuario.objects.create_user(
            "admin@correo.com", "admin1234", nombre="Lolo", apellido="Admin",
            rol=Rol.objects.create(nombre_rol="Administrador"),
        )
        self.ana = Usuario.objects.create_user("ana@correo.com", "clave1234", nombre="Ana", apellido="Pérez", rol=self.rol_est)
        self.luis = Usuario.objects.create_user("luis@correo.com", "clave1234", nombre="Luis", apellido="Mamani", rol=self.rol_est)
        dificultad = Dificultad.objects.create(nivel=1, nombre="Básico", multiplicador_xp=Decimal("1"))
        modulo = Modulo.objects.create(categoria=Categoria.objects.create(nombre="Alfabeto"), nombre="Alfabeto", orden=1)
        leccion = Leccion.objects.create(modulo=modulo, nombre="Letras", orden=1)
        tipo = TipoSena.objects.create(nombre="Estática")
        self.a = Sena.objects.create(leccion=leccion, tipo_sena=tipo, dificultad=dificultad, nombre="A", ruta_imagen="a.png")
        self.b = Sena.objects.create(leccion=leccion, tipo_sena=tipo, dificultad=dificultad, nombre="B", ruta_imagen="b.png")
        # A: 2 de 2 aciertos; B: 1 de 4 aciertos
        self._practicas(self.ana, self.a, [True, True])
        self._practicas(self.ana, self.b, [False, True])
        self._practicas(self.luis, self.b, [False, False])
        self.filtros = FiltroReporteForm().filtros()

    @staticmethod
    def _practicas(usuario, sena, resultados):
        for i, correcta in enumerate(resultados, start=1):
            Practica.objects.create(usuario=usuario, sena=sena, numero_intento=i, es_correcta=correcta,
                                    puntaje_obtenido=Decimal("90" if correcta else "40"), xp_ganado=30 if correcta else 0)


class ServiciosReporteTests(ReporteBase):
    def test_hu10_ca1_resumen_calcula_intentos_y_tasa(self):
        resumen = services.resumen(self.filtros)
        self.assertEqual(resumen["intentos"], 6)
        self.assertEqual(resumen["aciertos"], 3)
        self.assertEqual(resumen["tasa_acierto"], 50.0)
        self.assertEqual(resumen["estudiantes_activos"], 2)
        self.assertEqual(resumen["xp_otorgado"], 90)

    def test_hu10_ca1_por_sena_ordena_de_menor_a_mayor_acierto(self):
        filas = services.por_sena(self.filtros)
        self.assertEqual([f["sena"] for f in filas], ["B", "A"])
        self.assertEqual(filas[0]["tasa"], 25.0)

    def test_hu10_por_dia_incluye_dias_sin_practica(self):
        dias = services.por_dia(self.filtros)
        self.assertEqual(len(dias), 30)
        self.assertEqual(dias[-1]["dia"], timezone.localdate())
        self.assertEqual(sum(d["intentos"] for d in dias), 6)

    def test_hu10_por_estudiante_ordena_por_xp(self):
        filas = services.por_estudiante(self.filtros)
        self.assertEqual(filas[0]["correo"], "ana@correo.com")
        self.assertEqual(filas[0]["xp_periodo"], 90)

    def test_hu10_rango_invertido_es_invalido(self):
        form = FiltroReporteForm({"desde": "2026-10-20", "hasta": "2026-10-01"})
        self.assertFalse(form.is_valid())


class VistasReporteTests(ReporteBase):
    def test_hu10_estudiante_no_accede_al_dashboard(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("reportes:dashboard")).status_code, 403)

    def test_hu10_admin_ve_dashboard_con_indicadores(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes:dashboard"))
        self.assertContains(respuesta, "50.0 %")
        self.assertContains(respuesta, "datos-graficos")

    def test_hu10_ca2_exporta_excel_con_cuatro_hojas(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes:exportar_excel"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("attachment", respuesta["Content-Disposition"])
        libro = load_workbook(BytesIO(respuesta.content))
        self.assertEqual(libro.sheetnames, ["Resumen", "Por día", "Por seña", "Por estudiante"])
        self.assertEqual(libro["Por seña"]["A2"].value, "B")

    def test_hu10_ca2_exporta_pdf(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("reportes:exportar_pdf"))
        self.assertEqual(respuesta["Content-Type"], "application/pdf")
        self.assertTrue(respuesta.content.startswith(b"%PDF"))
