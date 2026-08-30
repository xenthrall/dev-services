"""
Punto de entrada de "alto nivel" a la lógica de negocio del manager.

Tanto la interfaz web (manager.web.app) como una futura CLI deberían llamar
a las funciones de este módulo en vez de usar env_loader, compose_reader o
docker_control directamente. Si el día de mañana cambia CÓMO se guarda la
configuración (por ejemplo, se agrega soporte para varios archivos .env),
solo hay que tocar este archivo.
"""

from __future__ import annotations

from . import docker_control
from .compose_reader import load_services as _load_services_from_compose
from .env_loader import load_env
from .errors import ConfigError
from .models import ServiceInfo


def get_services() -> tuple[list[ServiceInfo], str | None, list[str]]:
    """
    Devuelve (servicios, error, advertencias).

    - `error`: problema grave que nos impide saber qué servicios existen
      (en la práctica, docker-compose.yml ausente o inválido). Si no es
      None, `servicios` viene vacío y la interfaz debería mostrar solo
      este mensaje.
    - `advertencias`: problemas menores de los que la app se pudo
      recuperar (.env ausente, o no se pudo consultar el estado en
      Docker). La interfaz debería mostrarlas, pero igual listar los
      servicios con la mejor información disponible.
    """
    warnings: list[str] = []

    env, env_warning = load_env()
    if env_warning:
        warnings.append(env_warning)

    try:
        services = _load_services_from_compose(env)
    except ConfigError as exc:
        return [], str(exc), warnings

    statuses, status_warning = docker_control.get_statuses()
    if status_warning:
        warnings.append(status_warning)

    for service in services:
        state = statuses.get(service.name, "")
        service.status = "corriendo" if state == "running" else "detenido"

    return services, None, warnings
