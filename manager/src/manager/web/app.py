"""
Interfaz web: FastAPI + Jinja2 (HTML renderizado en el servidor) + HTMX
(para el auto-refresco y las acciones de iniciar/detener sin JavaScript
propio).

Este archivo se ocupa SOLO de "traducir" HTTP <-> HTML. Toda la lógica de
verdad (leer .env, leer docker-compose.yml, ejecutar docker) vive en
`manager.core`, que no sabe nada de FastAPI ni de HTML — así se puede
reusar esa lógica desde una CLI (u otra interfaz) el día de mañana.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from manager.core import docker_control
from manager.core.service_manager import get_services

app = FastAPI(title="dev-services manager")

# Las plantillas HTML viven junto a este archivo, en web/templates/.
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Página principal: carga la página completa una vez; el refresco
    periódico de las tarjetas lo hace HTMX contra /partials/services."""
    services, error, warnings = get_services()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "services": services,
            "error": error,
            "warnings": warnings,
            "last_action": None,
            "last_action_profile": None,
        },
    )


@app.get("/partials/services", response_class=HTMLResponse)
def services_partial(request: Request) -> HTMLResponse:
    """
    Fragmento HTML (sin <html>/<head>/<body>) con solo la grilla de
    tarjetas. HTMX lo pide automáticamente cada pocos segundos
    (ver el atributo hx-trigger="load, every 5s" en index.html) y
    reemplaza el contenido de la página con la respuesta, sin recargarla.
    """
    services, error, warnings = get_services()
    return templates.TemplateResponse(
        request,
        "_services.html",
        {
            "services": services,
            "error": error,
            "warnings": warnings,
            "last_action": None,
            "last_action_profile": None,
        },
    )


@app.post("/services/{profile}/start", response_class=HTMLResponse)
def start_service(request: Request, profile: str) -> HTMLResponse:
    """Botón "Iniciar" de una tarjeta: ejecuta `docker compose --profile
    <profile> up -d` y devuelve la grilla ya actualizada."""
    result = docker_control.start_service(profile)
    services, error, warnings = get_services()
    return templates.TemplateResponse(
        request,
        "_services.html",
        {
            "services": services,
            "error": error,
            "warnings": warnings,
            "last_action": result,
            "last_action_profile": profile,
        },
    )


@app.post("/services/{profile}/stop", response_class=HTMLResponse)
def stop_service(request: Request, profile: str) -> HTMLResponse:
    """Botón "Detener" de una tarjeta: ejecuta `docker compose --profile
    <profile> down` y devuelve la grilla ya actualizada."""
    result = docker_control.stop_service(profile)
    services, error, warnings = get_services()
    return templates.TemplateResponse(
        request,
        "_services.html",
        {
            "services": services,
            "error": error,
            "warnings": warnings,
            "last_action": result,
            "last_action_profile": profile,
        },
    )
