"""Validadores de contraseña del proyecto."""
import re

from django.core.exceptions import ValidationError


class LetrasYNumerosValidator:
    """Exige al menos una letra y un número en la contraseña."""

    def validate(self, password: str, user=None) -> None:
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise ValidationError(
                "La contraseña debe contener letras y números.",
                code="password_sin_letras_numeros",
            )

    def get_help_text(self) -> str:
        return "Tu contraseña debe contener al menos una letra y un número."
