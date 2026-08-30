"""
Lectura de ../docker-compose.yml y resolución de sus variables de entorno.

Esta es la parte que hace que la app sea "dinámica": en vez de tener una
lista de servicios escrita a mano en Python (algo así como
`SERVICES = ["postgres", "mysql", "redis"]`), leemos el propio
docker-compose.yml con PyYAML y descubrimos los servicios que existen, sus
perfiles, su imagen, sus puertos y sus variables de entorno. Si mañana
agregas un servicio nuevo al compose (siguiendo el mismo patrón que los
demás), aparecerá solo en la interfaz sin tocar este archivo.
"""

from __future__ import annotations

import re

import yaml

from .errors import ConfigError
from .models import ServiceInfo
from .paths import COMPOSE_FILE

# Coincide con ${VARIABLE} o ${VARIABLE:-default} tal como aparecen en
# docker-compose.yml (ej: "${POSTGRES_PORT:-5432}").
#   Grupo 1: nombre de la variable (POSTGRES_PORT)
#   Grupo 2: valor por defecto tras ":-", si lo hay (5432)
_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def _interpolate(value: str, env: dict[str, str]) -> str:
    """
    Reemplaza cada ${VARIABLE:-default} de `value` usando el diccionario
    `env` (lo que se leyó de .env). Es una versión simplificada de lo que
    hace "docker compose" internamente: si la variable está definida en
    `env` (y no es una cadena vacía) se usa ese valor; si no, se usa el
    valor por defecto indicado tras ":-"; si tampoco hay valor por
    defecto, se deja una cadena vacía.
    """

    def _replace(match: re.Match[str]) -> str:
        var_name, default = match.group(1), match.group(2)
        if env.get(var_name):
            return env[var_name]
        return default if default is not None else ""

    return _VAR_PATTERN.sub(_replace, value)


def _normalize_environment(raw_environment: object) -> dict[str, str]:
    """
    En un docker-compose.yml, la sección `environment:` de un servicio se
    puede escribir de dos formas equivalentes:

        environment:              environment:
          CLAVE: valor              - CLAVE=valor

    (diccionario) o (lista de strings "CLAVE=valor"). Esta función acepta
    cualquiera de las dos y siempre devuelve un dict[str, str] simple, para
    que el resto del código no tenga que preocuparse por el formato.
    """
    if isinstance(raw_environment, dict):
        return {str(key): "" if value is None else str(value) for key, value in raw_environment.items()}

    if isinstance(raw_environment, list):
        result: dict[str, str] = {}
        for item in raw_environment:
            key, _, value = str(item).partition("=")
            result[key] = value
        return result

    return {}


def _parse_port(ports_raw: object, env: dict[str, str]) -> tuple[str | None, int | None]:
    """
    Extrae (host, puerto) del primer mapeo de puertos de un servicio.

    Un mapeo típico en este repo es un string como:

        "127.0.0.1:${POSTGRES_PORT:-5432}:5432"

    con el formato host_ip:puerto_host:puerto_contenedor. Nos interesa el
    puerto_host (el que hay que usar para conectarse desde el sistema
    operativo anfitrión), después de resolver la variable de entorno.
    """
    if not isinstance(ports_raw, list) or not ports_raw:
        return None, None

    first = ports_raw[0]
    if not isinstance(first, str):
        # Compose también admite una forma "larga" (diccionario) para
        # describir puertos; no la usamos en este repo, así que la ignoramos
        # en vez de intentar soportar cada formato posible.
        return None, None

    resolved = _interpolate(first, env)
    parts = resolved.split(":")

    if len(parts) == 3:
        host_ip, host_port, _container_port = parts
    elif len(parts) == 2:
        host_ip, host_port = "0.0.0.0", parts[0]
    else:
        return None, None

    try:
        return host_ip, int(host_port)
    except ValueError:
        return host_ip, None


def _extract_credentials(environment: dict[str, str]) -> dict[str, str | None]:
    """
    Adivina, a partir del NOMBRE de cada variable de entorno (no de una
    lista fija de servicios conocidos), cuáles representan usuario,
    contraseña y base de datos:

    - termina en "_USER"                    -> usuario
    - termina en "_PASSWORD"                 -> contraseña
    - termina en "_DB" o "_DATABASE"         -> base de datos

    Esto funciona hoy para Postgres (POSTGRES_USER/PASSWORD/DB) y MySQL
    (MYSQL_USER/PASSWORD/DATABASE), y seguirá funcionando para cualquier
    servicio futuro que respete la misma convención de nombres, sin tener
    que enseñarle nada nuevo a este código.
    """
    user: str | None = None
    database: str | None = None
    password_candidates: dict[str, str] = {}

    for key, value in environment.items():
        upper_key = key.upper()
        if upper_key.endswith("_USER") and user is None:
            user = value
        elif upper_key.endswith("_PASSWORD"):
            password_candidates[upper_key] = value
        elif upper_key.endswith("_DB") or upper_key.endswith("_DATABASE"):
            database = value

    password: str | None = None
    if password_candidates:
        # MySQL define tanto MYSQL_ROOT_PASSWORD como MYSQL_PASSWORD; para la
        # tarjeta preferimos mostrar la del usuario de la app y no la de
        # root. Si solo existiera una contraseña "root", se muestra esa.
        non_root = {k: v for k, v in password_candidates.items() if "ROOT" not in k}
        chosen = non_root or password_candidates
        password = next(iter(chosen.values()))

    return {"user": user, "password": password, "database": database}


def load_services(env: dict[str, str]) -> list[ServiceInfo]:
    """
    Lee ../docker-compose.yml y devuelve la lista de servicios que define,
    con sus variables ya resueltas usando `env` (el resultado de
    env_loader.load_env()).

    Lanza ConfigError si el archivo no existe o no es un YAML válido: sin
    él no hay forma de saber qué servicios existen, así que se trata como
    un error grave (a diferencia de un .env ausente, que sí es recuperable).
    """
    if not COMPOSE_FILE.exists():
        raise ConfigError(f"No se encontró {COMPOSE_FILE.name} en {COMPOSE_FILE.parent}.")

    try:
        raw = yaml.safe_load(COMPOSE_FILE.read_text())
    except yaml.YAMLError as exc:
        raise ConfigError(f"{COMPOSE_FILE.name} no es un YAML válido: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"No se pudo leer {COMPOSE_FILE.name}: {exc}") from exc

    if not isinstance(raw, dict) or "services" not in raw:
        raise ConfigError(f"{COMPOSE_FILE.name} no define ninguna sección 'services'.")

    services: list[ServiceInfo] = []

    for name, definition in (raw["services"] or {}).items():
        definition = definition or {}

        # "profiles" es una lista en el YAML (un servicio podría, en teoría,
        # pertenecer a varios perfiles); en este repo cada servicio tiene
        # exactamente uno y coincide con su propio nombre, pero lo leemos
        # del archivo en vez de asumirlo.
        profiles = definition.get("profiles") or [name]
        profile = profiles[0]

        image = definition.get("image", "?")

        host, port = _parse_port(definition.get("ports"), env)

        environment = _normalize_environment(definition.get("environment"))
        environment_resolved = {key: _interpolate(value, env) for key, value in environment.items()}
        credentials = _extract_credentials(environment_resolved)

        services.append(
            ServiceInfo(
                name=name,
                profile=profile,
                image=image,
                host=host or "127.0.0.1",
                port=port,
                user=credentials["user"],
                password=credentials["password"],
                database=credentials["database"],
            )
        )

    # Orden alfabético para que el orden de las tarjetas sea predecible.
    services.sort(key=lambda service: service.name)
    return services
