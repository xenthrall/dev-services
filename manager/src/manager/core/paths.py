"""
Rutas importantes del proyecto.

Centralizamos aquí el cálculo de rutas para que el resto del código nunca
tenga que "adivinar" dónde está el .env o el docker-compose.yml: solo se
importan las constantes de este archivo.
"""

from __future__ import annotations

from pathlib import Path

# Path(__file__) apunta a este mismo archivo (paths.py). .resolve() lo
# convierte en una ruta absoluta, sin importar desde qué directorio se haya
# ejecutado el programa (esto es importante porque systemd, por ejemplo,
# puede arrancar el proceso con un cwd distinto al de este proyecto).
#
# .parents sube niveles en el árbol de carpetas:
#   parents[0] -> src/manager/core        (esta carpeta)
#   parents[1] -> src/manager             (el paquete Python "manager")
#   parents[2] -> src
#   parents[3] -> manager/                (la carpeta del proyecto uv, con pyproject.toml)
#   parents[4] -> dev-services/           (la raíz del repo, el padre de "manager/")
_THIS_FILE = Path(__file__).resolve()

MANAGER_DIR = _THIS_FILE.parents[3]
REPO_ROOT = MANAGER_DIR.parent

# Los dos archivos que esta app necesita leer, ambos en la raíz del repo
# (un nivel arriba de la carpeta "manager").
ENV_FILE = REPO_ROOT / ".env"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"
