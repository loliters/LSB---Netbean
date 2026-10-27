"""Crea un estudiante de demostración con 14 días de práctica, racha e insignias.

Uso:
    python manage.py cargar_demo              # crea el estudiante si no existe
    python manage.py cargar_demo --reiniciar  # borra su avance y lo vuelve a generar

Credenciales: estudiante.demo@netbean.com / Demo2026
Los datos son reales en la base de datos: el dashboard, el perfil y los reportes los leen igual
que los de cualquier estudiante.
"""
import random
from datetime import datetime, time, timedelta
from decimal import Decimal

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.contenido.models import Leccion, Sena
from apps.core.models import EstadoProgreso, Rol
from apps.gamificacion.models import UsuarioLogro
from apps.gamificacion.services import evaluar_logros
from apps.progreso.models import Practica, ProgresoLeccion, ProgresoSena
from apps.usuarios.models import EstadisticasUsuario, Usuario

CORREO = "estudiante.demo@netbean.com"
CLAVE = "Demo2026"
DIAS_RACHA = 6
XP = 30


class Command(BaseCommand):
    help = "Crea un estudiante de demostración con prácticas, racha e insignias."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true", help="Borra el avance del estudiante demo y lo regenera.")

    @transaction.atomic
    def handle(self, *args, **options):
        call_command("cargar_modulos", verbosity=0)
        call_command("cargar_logros", verbosity=0)
        aleatorio = random.Random(2026)
        usuario = Usuario.objects.filter(correo=CORREO).first()
        if usuario and not options["reiniciar"]:
            self.stdout.write(self.style.WARNING(f"Ya existe {CORREO}. Usa --reiniciar para regenerarlo."))
            return
        if usuario:
            UsuarioLogro.objects.filter(usuario=usuario).delete()
            Practica.objects.filter(usuario=usuario).delete()
            ProgresoSena.objects.filter(usuario=usuario).delete()
            ProgresoLeccion.objects.filter(usuario=usuario).delete()
        else:
            rol, _ = Rol.objects.get_or_create(nombre_rol="Estudiante")
            usuario = Usuario.objects.create_user(CORREO, CLAVE, nombre="Valeria", apellido="Quispe", rol=rol)

        senas = list(
            Sena.objects.filter(leccion__modulo__nombre__in=["Vocales", "Números del 1 al 5"], estado=True)
            .select_related("leccion").order_by("leccion__modulo__nombre", "leccion__orden", "id_sena")
        )
        hoy = timezone.localdate()
        # Días con práctica: los últimos 6 seguidos (racha) más algunos días anteriores
        dias = sorted({hoy - timedelta(days=d) for d in list(range(DIAS_RACHA)) + [8, 9, 11, 13]})
        practicas, intentos_por_sena = [], {}

        def agregar(sena, dia, correcta, minuto):
            numero = intentos_por_sena.get(sena.pk, 0) + 1
            intentos_por_sena[sena.pk] = numero
            puntaje = Decimal(str(aleatorio.randint(84, 98) if correcta else aleatorio.randint(45, 76)))
            momento = timezone.make_aware(datetime.combine(dia, time(18, 0)) + timedelta(minutes=minuto))
            practicas.append((Practica(usuario=usuario, sena=sena, numero_intento=numero, puntaje_obtenido=puntaje,
                                       xp_ganado=XP if correcta else 0, es_correcta=correcta), momento))

        for indice, dia in enumerate(dias):
            minuto = 0
            del_dia = senas[(indice * 3) % len(senas):] + senas[:(indice * 3) % len(senas)]
            for sena in del_dia[:4]:
                for _ in range(aleatorio.randint(0, 2)):
                    agregar(sena, dia, False, minuto)
                    minuto += 1
                agregar(sena, dia, True, minuto)
                minuto += 2
        # Asegura que todas las vocales y números queden dominados
        for sena in senas:
            if sena.pk not in intentos_por_sena:
                agregar(sena, hoy, True, 90)

        creadas = Practica.objects.bulk_create([p for p, _ in practicas])  # sin signals: datos históricos
        for practica, (_, momento) in zip(creadas, practicas):
            Practica.objects.filter(pk=practica.pk).update(fecha_practica=momento)

        for sena in senas:
            intentos = [p for p, _ in practicas if p.sena_id == sena.pk]
            mejor = max(p.puntaje_obtenido for p in intentos if p.es_correcta)
            ProgresoSena.objects.create(usuario=usuario, sena=sena, intentos=len(intentos), mejor_puntaje=mejor, dominada=True)
        completado = EstadoProgreso.objects.filter(nombre__iexact="Completado").first() or EstadoProgreso.objects.create(nombre="Completado")
        for leccion in Leccion.objects.filter(senas__in=senas).distinct():
            progreso = ProgresoLeccion.objects.create(usuario=usuario, leccion=leccion, estado=completado)
            ProgresoLeccion.objects.filter(pk=progreso.pk).update(
                fecha_inicio=timezone.now() - timedelta(days=13), fecha_completado=timezone.now() - timedelta(days=2))

        estadisticas, _ = EstadisticasUsuario.objects.get_or_create(usuario=usuario)
        estadisticas.xp_total = sum(p.xp_ganado for p, _ in practicas)
        estadisticas.total_practicas = len(practicas)
        estadisticas.racha_dias = DIAS_RACHA
        estadisticas.ultima_practica = hoy
        estadisticas.save()
        evaluar_logros(usuario, estadisticas)  # otorga insignias según los datos y suma su XP

        # Fechas de obtención escalonadas en el pasado para que el perfil se vea real
        for desfase, otorgado in enumerate(UsuarioLogro.objects.filter(usuario=usuario).order_by("logro__meta_valor")):
            UsuarioLogro.objects.filter(pk=otorgado.pk).update(fecha_obtencion=timezone.now() - timedelta(days=12 - min(desfase * 2, 12)))
        Usuario.objects.filter(pk=usuario.pk).update(ultimo_acceso=timezone.now())

        estadisticas.refresh_from_db()
        insignias = ", ".join(UsuarioLogro.objects.filter(usuario=usuario).values_list("logro__nombre", flat=True))
        self.stdout.write(self.style.SUCCESS(
            f"Estudiante demo listo: {CORREO} / {CLAVE}\n"
            f"{len(practicas)} prácticas · {estadisticas.xp_total} XP · racha {DIAS_RACHA} días\n"
            f"Insignias: {insignias}"))
