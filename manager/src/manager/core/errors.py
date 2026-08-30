"""Excepciones propias del paquete core."""

from __future__ import annotations


class ConfigError(Exception):
    """
    Se lanza cuando falta o es inválido algo sin lo cual la app no puede
    funcionar en absoluto: en la práctica, un docker-compose.yml ausente o
    con un YAML mal formado (sin él no sabemos ni qué servicios existen).

    Un .env ausente o ilegible NO usa esta excepción: se trata como una
    advertencia recuperable, porque el docker-compose.yml ya trae valores
    por defecto para cada variable. Ver core.env_loader.load_env().
    """
