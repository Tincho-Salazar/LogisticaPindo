@echo off
rem Arranca la API y la app movil. Ejecutar desde la carpeta backend. Requiere .env configurado y scripts\init_db.py ya corrido.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Creando entorno virtual...
  py -3.12 -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt
)
for /f "tokens=1,2 delims==" %%a in ('findstr /b "PORT=" .env') do set PORT=%%b
if "%PORT%"=="" set PORT=8000
echo Logistica Forestal Pindo SA en http://0.0.0.0:%PORT%  (Ctrl+C para detener)
rem Detras de un proxy inverso (Caddy/IIS) agregar: --forwarded-allow-ips 127.0.0.1
rem Un solo worker: en Windows uvicorn con --workers > 1 falla de forma intermitente al heredar el socket (WinError 10022).
.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port %PORT% --proxy-headers
