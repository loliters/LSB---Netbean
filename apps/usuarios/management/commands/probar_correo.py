"""Envía un correo de prueba y explica qué falla si no llega.

Uso:
    python manage.py probar_correo tu.correo@gmail.com
"""
import smtplib
import socket

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError

CONSOLA = "django.core.mail.backends.console.EmailBackend"


class Command(BaseCommand):
    help = "Envía un correo de prueba con la configuración actual y diagnostica los errores."

    def add_arguments(self, parser):
        parser.add_argument("destino", help="Correo que recibirá la prueba")

    def handle(self, *args, **options):
        destino = options["destino"]
        usuario = settings.EMAIL_HOST_USER
        self.stdout.write(
            f"Backend : {settings.EMAIL_BACKEND}\n"
            f"Servidor: {settings.EMAIL_HOST}:{settings.EMAIL_PORT} (TLS: {settings.EMAIL_USE_TLS})\n"
            f"Usuario : {usuario or '(vacío)'}\n"
            f"Remitente: {settings.DEFAULT_FROM_EMAIL}\n"
        )
        if settings.EMAIL_BACKEND == CONSOLA:
            self.stdout.write(self.style.WARNING(
                "El backend es el de CONSOLA: el correo se imprime aquí abajo y NO se envía.\n"
                "Para enviarlo de verdad configura EMAIL_BACKEND y las credenciales en .env (ver LEEME_CORREO.md) "
                "y borra la línea EMAIL_BACKEND de config/settings/dev.py.\n"))
        elif not usuario or not settings.EMAIL_HOST_PASSWORD:
            raise CommandError("Faltan EMAIL_HOST_USER o EMAIL_HOST_PASSWORD en el archivo .env.")
        try:
            send_mail("Prueba de correo de Net Bean", "Si lees esto, el envío de correos funciona.",
                      None, [destino], fail_silently=False)
        except smtplib.SMTPAuthenticationError:
            raise CommandError(
                "Gmail rechazó el usuario o la contraseña. Usa una «contraseña de aplicación» de 16 caracteres "
                "(no tu contraseña normal) y activa antes la verificación en dos pasos.") from None
        except smtplib.SMTPSenderRefused:
            raise CommandError("El remitente fue rechazado. DEFAULT_FROM_EMAIL debe usar la misma cuenta que EMAIL_HOST_USER.") from None
        except (socket.timeout, TimeoutError, ConnectionError, socket.gaierror, OSError) as error:
            raise CommandError(
                f"No hay conexión con {settings.EMAIL_HOST}:{settings.EMAIL_PORT} ({error}). "
                "Revisa tu internet, el firewall o el antivirus; prueba también EMAIL_PORT=465, EMAIL_USE_TLS=False y EMAIL_USE_SSL=True.") from None
        except smtplib.SMTPException as error:
            raise CommandError(f"El servidor de correo respondió con un error: {error}") from None
        self.stdout.write(self.style.SUCCESS(f"Listo: la prueba salió hacia {destino}. Revisa también la carpeta de spam."))
