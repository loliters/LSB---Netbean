"""Pruebas de la app contenido (HU-03)."""
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Modulo
from .services import listar_modulos_activos


class CategoriaModelTests(TestCase):
    """Pruebas del modelo Categoria."""

    def test_nombre_unico(self):
        """Una categoría no puede repetir nombre."""
        Categoria.objects.create(nombre='Alfabeto', descripcion='...')
        with self.assertRaises(IntegrityError):
            Categoria.objects.create(nombre='Alfabeto', descripcion='...')


class ModuloModelTests(TestCase):
    """Pruebas del modelo Modulo."""

    def setUp(self):
        self.categoria = Categoria.objects.create(
            nombre='Test', descripcion='...'
        )

    def test_hu03_ca1_orden_unico_por_categoria(self):
        """Dentro de una categoría no puede haber dos módulos con el mismo orden."""
        Modulo.objects.create(categoria=self.categoria, nombre='M1', orden=1)
        with self.assertRaises(IntegrityError):
            Modulo.objects.create(categoria=self.categoria, nombre='M2', orden=1)

    def test_orden_debe_ser_positivo(self):
        """CHECK: el orden debe ser > 0."""
        with self.assertRaises(IntegrityError):
            Modulo.objects.create(categoria=self.categoria, nombre='M', orden=0)

    def test_protegido_si_categoria_se_borra(self):
        """PROTECT: no se puede borrar una categoría con módulos."""
        Modulo.objects.create(categoria=self.categoria, nombre='M', orden=1)
        with self.assertRaises(Exception):
            self.categoria.delete()


class ListarModulosServiceTests(TestCase):
    """Pruebas del servicio listar_modulos_activos (HU-03)."""

    def test_hu03_ca1_retorna_categorias_con_modulos(self):
        """CA1: retorna lista de categorías con sus módulos."""
        cat = Categoria.objects.create(nombre='Alfabeto', descripcion='Señas')
        Modulo.objects.create(categoria=cat, nombre='Vocales', orden=1)

        resultado = listar_modulos_activos()

        self.assertEqual(len(resultado), 1)
        self.assertEqual(resultado[0]['nombre'], 'Alfabeto')
        self.assertEqual(len(resultado[0]['modulos']), 1)
        self.assertEqual(resultado[0]['modulos'][0]['nombre'], 'Vocales')

    def test_hu03_ca2_oculta_categorias_inactivas(self):
        """CA2: no retorna categorías con activo=False."""
        Categoria.objects.create(nombre='Inactiva', descripcion='...', activo=False)
        resultado = listar_modulos_activos()
        self.assertEqual(len(resultado), 0)

    def test_hu03_ca2_oculta_modulos_inactivos(self):
        """CA2: dentro de una categoría, no retorna módulos inactivos."""
        cat = Categoria.objects.create(nombre='Activa', descripcion='...')
        Modulo.objects.create(categoria=cat, nombre='Activo', orden=1, activo=True)
        Modulo.objects.create(categoria=cat, nombre='Inactivo', orden=2, activo=False)

        resultado = listar_modulos_activos()
        nombres = [m['nombre'] for m in resultado[0]['modulos']]
        self.assertIn('Activo', nombres)
        self.assertNotIn('Inactivo', nombres)

    def test_hu03_ca2_oculta_categoria_sin_modulos_activos(self):
        """CA2: no muestra categoría si no tiene módulos activos."""
        Categoria.objects.create(nombre='Vacía', descripcion='...')
        resultado = listar_modulos_activos()
        self.assertEqual(len(resultado), 0)

    def test_hu03_ca3_sin_categorias_devuelve_lista_vacia(self):
        """CA3: sin categorías activas, retorna lista vacía."""
        resultado = listar_modulos_activos()
        self.assertEqual(resultado, [])


class MapaModulosViewTests(TestCase):
    """Pruebas de la vista mapa_modulos (HU-03)."""

    def test_hu03_ca1_muestra_categorias_en_html(self):
        """CA1: la vista renderiza las categorías con módulos."""
        cat = Categoria.objects.create(
            nombre='Alfabeto', descripcion='Señas básicas'
        )
        Modulo.objects.create(categoria=cat, nombre='Vocales', orden=1)

        respuesta = self.client.get(reverse('contenido:mapa_modulos'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'Alfabeto')
        self.assertContains(respuesta, 'Vocales')

    def test_hu03_ca3_mensaje_sin_categorias(self):
        """CA3: mensaje informativo cuando no hay categorías."""
        respuesta = self.client.get(reverse('contenido:mapa_modulos'))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, 'No hay categorías activas')