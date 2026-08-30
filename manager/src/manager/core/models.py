"""
Estructuras de datos compartidas entre el lector de configuración, el
ejecutor de comandos docker y las distintas interfaces (web hoy, quizás
una CLI mañana). Al ser dataclasses simples, no dependen de FastAPI ni de
ningún otro framework: se pueden reusar desde cualquier lado.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ServiceInfo:
    """Toda la información de un servicio ya lista para mostrarse."""

    name: str
    """Nombre del servicio tal cual aparece en docker-compose.yml, ej: "postgres"."""

    profile: str
    """Perfil de Compose asociado (el que se usa con --profile). Normalmente
    es igual a `name`, pero se lee de verdad del compose por si algún día
    dejara de serlo."""

    image: str
    """Imagen Docker usada por el servicio, ej: "postgres:latest"."""

    host: str
    """Host desde el que se puede alcanzar el servicio (127.0.0.1 en este repo)."""

    port: int | None
    """Puerto publicado en el host, o None si el servicio no publica ninguno."""

    user: str | None
    password: str | None
    database: str | None

    status: str = "desconocido"
    """"corriendo" | "detenido" | "desconocido". Se calcula aparte, después
    de leer la configuración, preguntándole a Docker (ver docker_control.get_statuses)."""


@dataclass
class CommandResult:
    """Resultado de ejecutar un comando externo (docker compose up/down/ps...)."""

    success: bool
    message: str
