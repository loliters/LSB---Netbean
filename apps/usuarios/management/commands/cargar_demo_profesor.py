"""Crea un profesor de demostración con estudiantes asignados (HU-13).

Uso:
    python manage.py cargar_demo_profesor

Crea (o reutiliza) estos usuarios, todos con la contraseña Demo2026:
    profesor.demo@netbean.com   Profesor
    estudiante.demo@netbean.com Valeria  (con práctica, creada por cargar_demo)  → asignada
    lucia.demo@netbean.com      Lucía    (con algunos intentos)                  → asignada
    mateo.demo@netbean.com      Mateo    (sin práctica: sale «Sin actividad»)    → asignado
    pedro.demo@netbean.com      Pedro    (sin profesor: para probar «Asignarme»)

Es idempotente. No asigna contenido: así los estudiantes siguen viendo todo el catálogo hasta
que el profesor asigne algo desde «Asignar contenido».
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.contenido.models import Sena
from apps.core.models import Rol
from apps.gamificacion.services import registrar_intento
from apps.progreso.models import Practica
from apps.usuarios import asignaciones
from apps.usuarios.models import EstadisticasUsuario, Usuario

CLAVE = "Demo2026"
CORREO_PROFESOR = "profesor.demo@netbean.com"
CORREO_DEMO = "estudiante.demo@netbean.com"
ESTUDIANTES = [
    ("Lucía", "Mamani", "lucia.demo@netbean.com"),
    ("Mateo", "Condori", "mateo.demo@netbean.com"),
    ("Pedro", "Quispe", "pedro.demo@netbean.com"),
]


def _usuario(correo: str, nombre: str, apellido: str, nombre_rol: str) -> Usuario:
    usuario = Usuario.objects.filter(correo=correo).first()
    if usuario:
        return usuario
    rol = Rol.objects.filter(nombre_rol__iexact=nombre_rol).first() or Rol.objects.create(nombre_rol=nombre_rol)
    usuario = Usuario.objects.create_user(correo, CLAVE, nombre=nombre, apellido=apellido, rol=rol)
    if nombre_rol == "Estudiante":
        EstadisticasUsuario.objects.get_or_create(usuario=usuario)
    return usuario


class Command(BaseCommand):
    help = "Crea un profesor de demostración con estudiantes asignados."

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("cargar_modulos", verbosity=0)
        if not Usuario.objects.filter(correo=CORREO_DEMO).exists():
            call_command("cargar_demo", verbosity=0)
        profesor = _usuario(CORREO_PROFESOR, "Georgina", "Aruquipa", "Profesor")
        lucia, mateo, pedro = (_usuario(c, n, a, "Estudiante") for n, a, c in ESTUDIANTES)
        valeria = Usuario.objects.filter(correo=CORREO_DEMO).first()

        if not Practica.objects.filter(usuario=lucia).exists():
            vocales = list(Sena.objects.filter(leccion__modulo__nombre="Vocales").order_by("id_sena")[:2])
            for sena in vocales:
                registrar_intento(usuario=lucia, sena=sena, letra_predicha="Z", confianza=0.6)   # fallo
                registrar_intento(usuario=lucia, sena=sena, letra_predicha=sena.nombre, confianza=0.92)

        propios = [u.pk for u in (valeria, lucia, mateo) if u]
        nuevos = asignaciones.asignar_estudiantes(profesor, propios, asignado_por=profesor)
        self.stdout.write(self.style.SUCCESS(
            f"Profesor demo listo: {CORREO_PROFESOR} / {CLAVE}\n"
            f"Monitorea a {len(propios)} estudiantes ({nuevos} nuevos). Sin profesor: {pedro.correo}\n"
            "Mateo no tiene prácticas, así que aparece como «Sin actividad»."))
