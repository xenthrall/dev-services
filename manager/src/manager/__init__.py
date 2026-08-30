"""
Punto de entrada del paquete `manager`.

`uv run manager` ejecuta la función `main()` de aquí abajo (así está
declarado en pyproject.toml, sección [project.scripts]). Lo único que hace
es arrancar un servidor Uvicorn sirviendo la app de FastAPI definida en
manager.web.app.
"""

from __future__ import annotations

import os

import uvicorn

DEFAULT_PORT = 8787


def main() -> None:
    # El puerto se puede cambiar sin tocar código con la variable de entorno
    # MANAGER_PORT (ver el README.md de esta carpeta para más detalle,
    # incluyendo cómo configurarlo en el servicio de systemd).
    port = int(os.environ.get("MANAGER_PORT", DEFAULT_PORT))

    # host="127.0.0.1": igual que los servicios de Docker, el manager solo
    # escucha en localhost, no en toda la red.
    uvicorn.run("manager.web.app:app", host="127.0.0.1", port=port)
