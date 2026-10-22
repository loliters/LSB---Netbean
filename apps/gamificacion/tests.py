"""Pruebas de XP, racha y Signals (HU-06, HU-07)."""
import json
from datetime import date
from decimal import Decimal
from unittest import mock

from django.test import TestCase, override_settings
from django.urls import reverse

from apps.contenido.models import Leccion, Modulo, Sena
from apps.core.models import Categoria, Dificultad, Rol, TipoSena
from apps.progreso.models import Practica, ProgresoLeccion, ProgresoSena
from apps.usuarios.models import EstadisticasUsuario, Usuario
from ia.predictor import Prediccion

from . import services


class BaseGamificacion(TestCase):
    def setUp(self):
        rol = Rol.objects.create(nombre_rol="Estudiante")
        self.usuario = Usuario.objects.create_user(
            "ana@correo.com", "clave1234", nombre="Ana", apellido="Pérez", rol=rol
        )
        categoria = Categoria.objects.create(nombre="Alfabeto")
        dificultad = Dificultad.objects.create(nivel=1, nombre="Básico", multiplicador_xp=Decimal("1.00"))
        modulo = Modulo.objects.create(categoria=categoria, dificultad=dificultad, nombre="Alfabeto", orden=1)
        self.leccion = Leccion.objects.create(modulo=modulo, nombre="Letras A-E", orden=1)
        self.sena = Sena.objects.create(
            leccion=self.leccion,
            tipo_sena=TipoSena.objects.create(nombre="Estática"),
            dificultad=dificultad,
            nombre="B",
            ruta_imagen="senas/b.png",
        )

    def estadisticas(self):
        return EstadisticasUsuario.objects.get(usuario=self.usuario)


class SignalXpTests(BaseGamificacion):
    def test_hu06_acierto_suma_30_xp_racha_y_guarda_practica(self):
        resultado = services.registrar_intento(
            usuario=self.usuario, sena=self.sena, letra_predicha="b", confianza=0.9
        )
        stats = self.estadisticas()
        self.assertTrue(resultado["es_correcta"])
        self.assertEqual(stats.xp_total, 30)
        self.assertEqual(stats.racha_dias, 1)
        self.assertEqual(stats.total_practicas, 1)
        practica = Practica.objects.get(usuario=self.usuario, sena=self.sena)
        self.assertEqual(practica.xp_ganado, 30)
        self.assertEqual(practica.puntaje_obtenido, Decimal("90.00"))

    def test_hu06_signal_se_dispara_al_crear_practica_directamente(self):
        Practica.objects.create(
            usuario=self.usuario, sena=self.sena, numero_intento=1,
            puntaje_obtenido=Decimal("95"), xp_ganado=30,
        )
        self.assertEqual(self.estadisticas().xp_total, 30)

    def test_hu06_signal_no_suma_dos_veces_al_actualizar(self):
        practica = Practica.objects.create(
            usuario=self.usuario, sena=self.sena, numero_intento=1,
            puntaje_obtenido=Decimal("95"), xp_ganado=30,
        )
        practica.save()
        self.assertEqual(self.estadisticas().xp_total, 30)

    def test_hu07_fallo_registra_intento_sin_xp(self):
        resultado = services.registrar_intento(
            usuario=self.usuario, sena=self.sena, letra_predicha="A", confianza=0.8
        )
        stats = self.estadisticas()
        self.assertFalse(resultado["es_correcta"])
        self.assertEqual(stats.xp_total, 0)
        self.assertEqual(stats.total_practicas, 1)
        self.assertEqual(stats.racha_dias, 0)

    def test_hu07_numero_de_intento_incrementa(self):
        for letra in ("A", "C"):
            services.registrar_intento(usuario=self.usuario, sena=self.sena, letra_predicha=letra, confianza=0.5)
        self.assertEqual(Practica.objects.filter(usuario=self.usuario).count(), 2)
        self.assertEqual(ProgresoSena.objects.get(usuario=self.usuario, sena=self.sena).intentos, 2)

    def test_hu07_letra_correcta_bajo_el_minimo_no_aprueba(self):
        self.sena.puntos_minimos = 80
        self.sena.save()
        resultado = services.registrar_intento(
            usuario=self.usuario, sena=self.sena, letra_predicha="B", confianza=0.75
        )
        self.assertFalse(resultado["es_correcta"])
        self.assertTrue(resultado["letra_coincide"])
        self.assertEqual(self.estadisticas().xp_total, 0)

    def test_hu06_dominar_todas_las_senas_completa_la_leccion(self):
        resultado = services.registrar_intento(
            usuario=self.usuario, sena=self.sena, letra_predicha="B", confianza=0.95
        )
        self.assertTrue(resultado["leccion_completada"])
        progreso = ProgresoLeccion.objects.get(usuario=self.usuario, leccion=self.leccion)
        self.assertIsNotNone(progreso.fecha_completado)
        self.assertEqual(progreso.estado.nombre, "Completado")

    @override_settings(XP_ENFRIAMIENTO_SEGUNDOS=10)
    def test_hu06_aciertos_en_rafaga_no_duplican_xp(self):
        for _ in range(2):
            services.registrar_intento(usuario=self.usuario, sena=self.sena, letra_predicha="B", confianza=0.9)
        self.assertEqual(self.estadisticas().xp_total, 30)


class RachaTests(TestCase):
    def test_racha_mismo_dia_se_mantiene(self):
        self.assertEqual(services.calcular_racha(3, date(2026, 10, 15), date(2026, 10, 15)), 3)

    def test_racha_dia_consecutivo_suma(self):
        self.assertEqual(services.calcular_racha(3, date(2026, 10, 14), date(2026, 10, 15)), 4)

    def test_racha_con_hueco_reinicia(self):
        self.assertEqual(services.calcular_racha(3, date(2026, 10, 10), date(2026, 10, 15)), 1)


class EvaluarEndpointTests(BaseGamificacion):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.usuario)
        self.url = reverse("gamificacion:evaluar")

    def _post(self, **cuerpo):
        return self.client.post(self.url, json.dumps(cuerpo), content_type="application/json")

    def test_leccion_inexistente_responde_404(self):
        respuesta = self._post(id_leccion=9999, id_sena=self.sena.pk, frame="x")
        self.assertEqual(respuesta.status_code, 404)
        self.assertFalse(Practica.objects.exists())

    def test_sena_de_otra_leccion_responde_404(self):
        respuesta = self._post(id_leccion=self.leccion.pk, id_sena=9999, frame="x")
        self.assertEqual(respuesta.status_code, 404)

    @mock.patch("apps.gamificacion.views.predecir_desde_base64")
    def test_evaluar_acierto_devuelve_xp_actualizado(self, predecir):
        predecir.return_value = Prediccion(letra="B", confianza=0.88, mano_detectada=True)
        respuesta = self._post(id_leccion=self.leccion.pk, id_sena=self.sena.pk, frame="x")
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.json()
        self.assertTrue(datos["es_correcta"])
        self.assertEqual(datos["xp_total"], 30)

    @mock.patch("apps.gamificacion.views.predecir_desde_base64")
    def test_sin_mano_no_registra_practica(self, predecir):
        predecir.return_value = Prediccion(letra=None, confianza=0.0, mano_detectada=False)
        respuesta = self._post(id_leccion=self.leccion.pk, id_sena=self.sena.pk, frame="x")
        self.assertFalse(respuesta.json()["registrado"])
        self.assertFalse(Practica.objects.exists())