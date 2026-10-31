""" Punto de arranque en Python puro (sin .bat).
Lee HOST y PORT/APP_PORT desde .env y levanta el servidor escuchando en localhost y en todas las IPs del equipo.
Uso:
    python run.py
    .venv\\Scripts\\python run.py
"""
import os
import socket
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
VENV_PY = BASE_DIR / ".venv" / "Scripts" / "python.exe"

# Si se ejecuta con el Python global fuera del .venv, delega automáticamente en el .venv local
if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
    import subprocess
    raise SystemExit(subprocess.call([str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]]))

os.chdir(BASE_DIR)
sys.path.insert(0, str(BASE_DIR))

import uvicorn  # noqa: E402
from app import config  # noqa: E402


def _ips_locales() -> list[str]:
    ips: list[str] = []
    try:
        _, _, addr_list = socket.gethostbyname_ex(socket.gethostname())
        for ip in addr_list:
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            if ip and not ip.startswith("127.") and ip not in ips:
                ips.insert(0, ip)
    except OSError:
        pass
    return ips


def _puede_bindear(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False


def _liberar_puerto(host: str, port: int) -> int:
    if _puede_bindear(host, port):
        return port
    import subprocess
    import time

    print(f"Puerto {port} en uso por una instancia previa; intentando liberar...")
    cmd = (
        f"$pids = @(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique); "
        "if ($pids) { "
        "  foreach ($p in $pids) { "
        "    Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; "
        "    Get-CimInstance Win32_Process -Filter \"ParentProcessId = $p AND Name = 'python.exe'\" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue } "
        "  } "
        "}"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True)
    time.sleep(0.5)
    if _puede_bindear(host, port):
        return port

    # Si sigue ocupado (p. ej. procesos python.exe huérfanos iniciados como Administrador), buscar el siguiente libre
    alt = port + 1 if port != 8000 else 8080
    while not _puede_bindear(host, alt):
        alt += 1
    print(f"AVISO: El puerto {port} está retenido por un proceso con permisos de Administrador.")
    print("       Para liberar el 8000 en una consola como Administrador: taskkill /F /IM python.exe")
    print(f"       Usando puerto alternativo libre: {alt} (o cambiá PORT en backend/.env)")
    return alt


def main():
    host = config.HOST or "0.0.0.0"
    port = _liberar_puerto(host, config.PORT)
    ips = _ips_locales()

    print("=" * 64)
    print(f" Logística Forestal Pindó SA · Entorno: {config.APP_ENV}")
    print(f" Escuchando en {host}:{port} (Ctrl+C para detener)")
    print("-" * 64)
    print(f"  -> Localhost:  http://localhost:{port}")
    print(f"  -> Loopback:   http://127.0.0.1:{port}")
    for ip in ips:
        print(f"  -> Red / IP:   http://{ip}:{port}")
    print("=" * 64)

    uvicorn.run(
        "app.main:app",
        host=host,
        port=port,
        proxy_headers=True,
        forwarded_allow_ips="*",
    )


if __name__ == "__main__":
    main()
