# manager

Panel web local para iniciar y detener, uno por uno, los servicios Docker
definidos en `../docker-compose.yml` (Postgres, MySQL, Redis, y cualquier
otro que se agregue después siguiendo el mismo patrón).

Corre **directamente en el sistema host** (no dentro de un contenedor):
necesita ejecutar `docker compose` contra el `docker-compose.yml` del repo
padre, así que meterlo en un contenedor obligaría a exponerle el socket de
Docker sin necesidad real.

## Cómo está organizado el código

```
manager/
├── src/manager/
│   ├── core/              # lógica de negocio, sin nada de web
│   │   ├── paths.py            # dónde están .env y docker-compose.yml
│   │   ├── env_loader.py       # lee ../.env
│   │   ├── compose_reader.py   # lee ../docker-compose.yml y resuelve variables
│   │   ├── docker_control.py   # ejecuta "docker compose ..." con subprocess
│   │   ├── service_manager.py  # junta todo lo anterior en una sola función
│   │   ├── models.py           # ServiceInfo, CommandResult (dataclasses)
│   │   └── errors.py           # ConfigError
│   └── web/                # interfaz web (FastAPI + Jinja2 + HTMX)
│       ├── app.py              # rutas HTTP
│       └── templates/          # HTML (Jinja2 + Tailwind por CDN)
└── pyproject.toml
```

La idea de separar `core/` de `web/` es que **toda la lógica que no es de
interfaz** (leer configuración, ejecutar Docker) no sabe nada de FastAPI ni
de HTML. Si en el futuro querés agregar, por ejemplo, un comando de línea
de comandos (`manager status`, `manager start postgres`, etc.), esa CLI
podría importar directamente `manager.core.service_manager` y
`manager.core.docker_control` sin duplicar ni una línea de esta lógica.
Cada archivo de `core/` tiene comentarios explicando el porqué de las
partes menos obvias (lectura del `.env`, parseo del `docker-compose.yml`,
uso de `subprocess`).

## Requisitos

- [uv](https://docs.astral.sh/uv/) instalado (`uv --version`).
- Docker Engine + el plugin de Compose, ya usados por el repo padre.
- Haber copiado `../.env.example` a `../.env` (ver el README de la raíz del
  repo). Si no lo hiciste, el manager igual funciona: muestra una
  advertencia y usa los valores por defecto del `docker-compose.yml`.

`uv` se encarga de crear el entorno virtual y descargar las dependencias
por su cuenta; no hace falta `pip install` ni activar nada a mano.

## Modo desarrollo

Desde esta carpeta (`dev-services/manager/`):

```bash
# Arranca con auto-reload: la app se reinicia sola cada vez que guardás
# un archivo .py o .html. Ideal mientras estás editando el código.
uv run uvicorn manager.web.app:app --reload --host 127.0.0.1 --port 8787
```

También existe un atajo sin auto-reload, pensado para "solo quiero que
esté corriendo" (es el mismo comando que usa el servicio de systemd más
abajo):

```bash
uv run manager
```

Con cualquiera de los dos, abrí <http://127.0.0.1:8787> en el navegador.

## Puerto por defecto

El manager escucha por defecto en el puerto **8787**, solo en
`127.0.0.1` (no en toda la red local, igual que los servicios de Docker
del repo padre).

- Con `uv run uvicorn ...`, cambiá el puerto con el flag `--port`:
  ```bash
  uv run uvicorn manager.web.app:app --reload --port 9000
  ```
- Con `uv run manager` (y con el servicio de systemd), cambiá el puerto
  con la variable de entorno `MANAGER_PORT`:
  ```bash
  MANAGER_PORT=9000 uv run manager
  ```

## Correr como servicio de systemd (usuario)

Esto deja el manager corriendo en segundo plano todo el tiempo, y hace que
vuelva a arrancar solo si el sistema se reinicia (una vez que inicies
sesión) o si el proceso se cae.

1. Confirmá dónde está instalado `uv`:

   ```bash
   which uv
   # ejemplo de salida: /home/jhon/.local/bin/uv
   ```

2. Creá el archivo de unidad en
   `~/.config/systemd/user/dev-services-manager.service` con el siguiente
   contenido. Ajustá `WorkingDirectory` y la ruta de `uv` en `ExecStart` si
   difieren de tu instalación:

   ```ini
   [Unit]
   Description=dev-services manager (panel web local)
   After=network.target

   [Service]
   Type=simple
   WorkingDirectory=%h/Escritorio/dev-services/manager
   ExecStart=%h/.local/bin/uv run manager
   Environment=MANAGER_PORT=8787
   Restart=on-failure
   RestartSec=3

   [Install]
   WantedBy=default.target
   ```

   (`%h` es el `$HOME` del usuario dueño de la sesión systemd --user; systemd
   lo reemplaza automáticamente.)

3. Recargá systemd y arrancá el servicio:

   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now dev-services-manager.service
   ```

4. Comandos útiles para el día a día:

   ```bash
   systemctl --user status dev-services-manager.service   # ver si está corriendo
   journalctl --user -u dev-services-manager.service -f   # ver logs en vivo
   systemctl --user restart dev-services-manager.service  # reiniciar (ej. tras cambiar código)
   systemctl --user stop dev-services-manager.service     # detener
   systemctl --user disable dev-services-manager.service  # que no arranque solo
   ```

5. Para que el servicio siga corriendo aunque cierres sesión (no solo
   mientras estás logueado), habilitá "lingering" una sola vez:

   ```bash
   sudo loginctl enable-linger "$USER"
   ```

   Sin este paso, systemd --user (y por lo tanto el manager) se detiene
   cuando cerrás sesión gráfica o SSH.

## Notas

- El manager nunca ejecuta comandos de Docker "a ciegas": los botones
  Iniciar/Detener llaman siempre a `docker compose --profile <perfil> up
  -d` / `down`, exactamente los mismos comandos que usarías a mano desde
  la terminal (ver el README de la raíz del repo).
- Las contraseñas se muestran en texto plano en la interfaz a propósito:
  es una herramienta personal para uso 100% local (`127.0.0.1`), pensada
  para copiar credenciales rápido al configurar una app. No expongas este
  panel fuera de tu propia máquina.
