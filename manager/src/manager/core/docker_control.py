"""
Ejecución de comandos "docker compose" contra el repo padre (dev-services).

Toda la interacción con `subprocess` vive en este único archivo. Si más
adelante agregas una CLI (línea de comandos) además de la interfaz web,
debería importar y reusar estas mismas funciones en vez de volver a llamar
a `subprocess` por su cuenta.
"""

from __future__ import annotations

import json
import subprocess

from .models import CommandResult
from .paths import REPO_ROOT

# Tiempo máximo, en segundos, que esperamos a que termine un comando. "up -d"
# puede tardar bastante si Docker tiene que descargar la imagen por primera vez.
_ACTION_TIMEOUT = 120
_STATUS_TIMEOUT = 20


def _run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    """
    Wrapper delgado sobre `subprocess.run` para lanzar "docker compose <args>".

    Tres detalles importantes para quien esté aprendiendo:

    - `cwd=REPO_ROOT`: el comando se ejecuta como si antes hubiéramos hecho
      `cd` a la raíz del repo (donde vive docker-compose.yml). Así da igual
      desde qué carpeta se haya arrancado este programa.
    - `capture_output=True, text=True`: en vez de dejar que la salida del
      comando se imprima directo en la terminal, la capturamos como texto
      (stdout/stderr) para poder mostrarla en la página web.
    - NO usamos `check=True`: si el comando falla (código de salida != 0),
      `subprocess.run` no lanza ninguna excepción; somos nosotros quienes
      revisamos `result.returncode` a mano en cada función de abajo.
    """
    return subprocess.run(
        ["docker", "compose", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def start_service(profile: str) -> CommandResult:
    """Ejecuta: docker compose --profile <profile> up -d"""
    try:
        result = _run(["--profile", profile, "up", "-d"], timeout=_ACTION_TIMEOUT)
    except FileNotFoundError:
        return CommandResult(False, "No se encontró el comando 'docker'. ¿Está instalado y en el PATH?")
    except subprocess.TimeoutExpired:
        return CommandResult(False, f"El comando no respondió en {_ACTION_TIMEOUT}s (¿se está descargando una imagen grande?).")

    if result.returncode == 0:
        return CommandResult(True, f"'{profile}' iniciado correctamente.")
    return CommandResult(False, result.stderr.strip() or "docker compose up falló sin más detalles.")


def stop_service(profile: str) -> CommandResult:
    """Ejecuta: docker compose --profile <profile> down"""
    try:
        result = _run(["--profile", profile, "down"], timeout=_ACTION_TIMEOUT)
    except FileNotFoundError:
        return CommandResult(False, "No se encontró el comando 'docker'. ¿Está instalado y en el PATH?")
    except subprocess.TimeoutExpired:
        return CommandResult(False, f"El comando no respondió en {_ACTION_TIMEOUT}s.")

    if result.returncode == 0:
        return CommandResult(True, f"'{profile}' detenido correctamente.")
    return CommandResult(False, result.stderr.strip() or "docker compose down falló sin más detalles.")


def get_statuses() -> tuple[dict[str, str], str | None]:
    """
    Devuelve ({nombre_de_servicio: estado}, advertencia).

    Detalle importante: usamos `docker compose ps` SIN `--profile`. Una vez
    que un contenedor ya fue creado, `ps` lo lista sin importar con qué
    perfil se haya iniciado (los perfiles solo controlan qué se crea con
    `up`, no qué se lista con `ps`). Así que una sola llamada nos alcanza
    para conocer el estado de TODOS los servicios, en vez de tener que
    llamar a `docker compose` una vez por cada uno.

    Pedimos `--format json` para no tener que interpretar una tabla de texto:
    docker compone imprime un objeto JSON por línea (uno por contenedor).
    """
    try:
        result = _run(["ps", "--format", "json"], timeout=_STATUS_TIMEOUT)
    except FileNotFoundError:
        return {}, "No se encontró el comando 'docker'. No se puede saber qué servicios están corriendo."
    except subprocess.TimeoutExpired:
        return {}, "Docker no respondió a tiempo al consultar el estado de los servicios."

    if result.returncode != 0:
        message = result.stderr.strip() or "docker compose ps falló sin más detalles."
        return {}, f"No se pudo consultar el estado de los servicios: {message}"

    statuses: dict[str, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            # Una línea inesperada no debería tirar abajo toda la consulta;
            # simplemente la ignoramos.
            continue
        statuses[entry.get("Service", "")] = entry.get("State", "")

    return statuses, None
