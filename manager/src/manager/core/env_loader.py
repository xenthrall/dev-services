"""
Carga de variables de entorno desde el archivo ../.env (el .env que vive en
la raíz del repo dev-services, un nivel arriba de "manager/").
"""

from __future__ import annotations

from dotenv import dotenv_values

from .paths import ENV_FILE


def load_env() -> tuple[dict[str, str], str | None]:
    """
    Lee ../.env y devuelve (variables, advertencia).

    Puntos clave:

    - Usamos `dotenv_values(ENV_FILE)` en vez de `load_dotenv()`. La
      diferencia importa: `load_dotenv()` mete las variables directamente en
      `os.environ` (el entorno del propio proceso Python), mientras que
      `dotenv_values()` solo LEE el archivo y nos devuelve un diccionario
      normal. Preferimos esto último para no mezclar las credenciales de
      los servicios de Docker con el entorno del propio manager.

    - Si el archivo no existe, o no se puede leer, NO lanzamos una excepción:
      el docker-compose.yml ya define un valor por defecto para cada
      variable con la sintaxis ${VARIABLE:-default} (ver compose_reader.py),
      así que la app puede seguir mostrando esos valores por defecto.
      En su lugar, devolvemos un diccionario vacío junto con un mensaje de
      advertencia legible, para que la interfaz avise sin dejar de funcionar.
    """
    if not ENV_FILE.exists():
        return {}, (
            f"No se encontró {ENV_FILE.name} en {ENV_FILE.parent}. "
            "Copia .env.example a .env para usar tus propias credenciales y "
            "puertos; mientras tanto se muestran los valores por defecto "
            "definidos en docker-compose.yml."
        )

    try:
        raw = dotenv_values(ENV_FILE)
    except Exception as exc:  # noqa: BLE001 - cualquier fallo de lectura/parseo cuenta aquí
        return {}, (
            f"No se pudo leer {ENV_FILE.name} ({exc}). "
            "Se están usando los valores por defecto de docker-compose.yml."
        )

    # dotenv_values puede devolver None como valor si una línea del archivo
    # no tiene la forma "CLAVE=valor" (ej. una línea vacía o mal escrita).
    # Los convertimos a "" para que el resto del código solo trabaje con str.
    env = {key: (value if value is not None else "") for key, value in raw.items()}
    return env, None
