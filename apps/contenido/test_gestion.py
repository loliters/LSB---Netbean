"""Pruebas de gestión de módulos, lecciones y señas (HU-08)."""
import shutil
import tempfile
from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.core.models import Categoria, Dificultad, Rol, TipoSena
from apps.usuarios.models import Usuario

from .models import Leccion, Modulo, Sena

MEDIA_TEMPORAL = tempfile.mkdtemp()
ETIQUETAS_TEMPORALES = Path(tempfile.mkdtemp()) / "etiquetas.txt"
ETIQUETAS_TEMPORALES.write_text("A\nB\nC\n_\n", encoding="utf-8")


def imagen_png(nombre="b.png"):
    buffer = BytesIO()
    Image.new("RGB", (20, 20), "white").save(buffer, format="PNG")
    return SimpleUploadedFile(nombre, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL, RUTA_ETIQUETAS=ETIQUETAS_TEMPORALES)
class GestionContenidoTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        def usuario(correo, rol):
            return Usuario.objects.create_user(correo, "clave1234", nombre="X", apellido="Y",
                                               rol=Rol.objects.get_or_create(nombre_rol=rol)[0])
        self.profesor = usuario("profe@correo.com", "Profesor")
        self.estudiante = usuario("est@correo.com", "Estudiante")
        self.categoria = Categoria.objects.create(nombre="Alfabeto")
        self.dificultad = Dificultad.objects.create(nivel=1, nombre="Básico", multiplicador_xp=Decimal("1"))
        self.tipo = TipoSena.objects.create(nombre="Estática")
        self.modulo = Modulo.objects.create(categoria=self.categoria, nombre="Alfabeto", orden=1)
        self.leccion = Leccion.objects.create(modulo=self.modulo, nombre="Letras A-E", orden=1)
        self.client.force_login(self.profesor)

    def _datos_sena(self, **extra):
        return {"nombre": "b", "tipo_sena": self.tipo.pk, "dificultad": self.dificultad.pk,
                "puntos_minimos": 80, "imagen": imagen_png(), **extra}

    def test_hu08_estudiante_no_accede_a_la_gestion(self):
        self.client.force_login(self.estudiante)
        self.assertEqual(self.client.get(reverse("contenido:gestion_modulos")).status_code, 403)

    def test_hu08_profesor_crea_modulo(self):
        self.client.post(reverse("contenido:gestion_modulo_nuevo"), {
            "categoria": self.categoria.pk, "nombre": "Saludos", "orden": 2, "xp_recompensa": 50})
        self.assertTrue(Modulo.objects.filter(nombre="Saludos").exists())

    def test_hu08_ca3_orden_repetido_en_el_modulo_se_rechaza(self):
        url = reverse("contenido:gestion_leccion_nueva", args=[self.modulo.pk])
        respuesta = self.client.post(url, {"nombre": "Otra", "orden": 1, "xp_recompensa": 0})
        self.assertContains(respuesta, "Ya existe una lección con ese orden")
        self.assertEqual(self.modulo.lecciones.count(), 1)

    def test_hu08_ca1_crea_sena_con_imagen_y_nombre_en_mayusculas(self):
        url = reverse("contenido:gestion_sena_nueva", args=[self.leccion.pk])
        self.client.post(url, self._datos_sena())
        sena = Sena.objects.get(leccion=self.leccion)
        self.assertEqual(sena.nombre, "B")
        self.assertTrue(sena.ruta_imagen.startswith("senas/"))
        self.assertTrue((Path(MEDIA_TEMPORAL) / sena.ruta_imagen).exists())

    def test_hu08_rechaza_archivo_que_no_es_imagen(self):
        url = reverse("contenido:gestion_sena_nueva", args=[self.leccion.pk])
        falso = SimpleUploadedFile("b.png", b"no es una imagen", content_type="image/png")
        self.client.post(url, self._datos_sena(imagen=falso))
        self.assertFalse(Sena.objects.exists())

    def test_hu08_rechaza_sena_que_el_modelo_no_reconoce(self):
        url = reverse("contenido:gestion_sena_nueva", args=[self.leccion.pk])
        respuesta = self.client.post(url, self._datos_sena(nombre="HOLA"))
        self.assertContains(respuesta, "El modelo de IA no reconoce")

    def test_hu08_ca2_desactivar_modulo_lo_oculta_del_catalogo(self):
        self.client.post(reverse("contenido:gestion_estado", args=["modulo", self.modulo.pk]))
        self.modulo.refresh_from_db()
        self.assertFalse(self.modulo.estado)
        respuesta = self.client.get(reverse("contenido:mapa_modulos"))
        self.assertNotContains(respuesta, "Ver módulo")
