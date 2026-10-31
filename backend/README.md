# Logística Forestal Pindó SA · backend + app móvil

API en Python (FastAPI) sobre SQL Server 2012 (base `sapinfo`, tablas `ZTLOGI_*`) y app móvil en HTML5/CSS/JavaScript (PWA, sin frameworks) servida por el mismo proceso. Un solo servicio, una sola carpeta.

```
backend/
  app/            API: config, db (pyodbc), auth (Argon2 + JWT), reglas (negocio puro), routers/*, reportes (PDF), ocr (visión)
  static/         app móvil: index.html, app.css, api.js (sesión + cola offline), util.js, views.js, sheets.js, app.js, sw.js, manifest.json
  schema.sql      esquema idempotente de las 30 tablas ZTLOGI_* (SQL Server 2012)
  scripts/        init_db.py (crea tablas, catálogos mínimos y admin) · seed_demo.py (datos de ejemplo) · reset_demo.py (borra y re-siembra; sólo dev)
  tests/          test_reglas.py (reglas de negocio) · test_api.py (integración completa contra la base local)
  data/fotos/     fotos de remitos (se crea sola)
  .env            configuración ACTUAL: desarrollo en esta PC (SQL Express local) · .env.prod: plantilla para 192.168.30.5\PRD (todavía no en uso)
  run.bat         arranque en Windows
```

## 0. Estado actual: desarrollo en esta PC

Mientras dure el desarrollo todo corre contra el SQL Server 2012 Express local (`.\SQLEXPRESS`, base `sapinfo`, autenticación de Windows) que ya tiene las tablas y los datos demo cargados. No se toca `192.168.30.5`. Ver sección 2.

## 1. Puesta en marcha en producción (más adelante)

Requisitos: Python 3.12, "ODBC Driver 17 for SQL Server" (ya instalado en este equipo), acceso a `192.168.30.5\PRD`.

1. Completar en `.env.prod`: `DB_USER`, `DB_PASSWORD` (usuario SQL con permisos de crear tablas en `sapinfo` la primera vez; luego alcanza con lectura/escritura sobre `ZTLOGI_*`) y `ADMIN_PASSWORD` (8+ caracteres). Después `copy .env.prod .env` (o arrancar con `set LF_ENV=.env.prod` para no pisar el `.env` local).
2. Crear entorno e instalar dependencias:
   ```
   py -3.12 -m venv .venv
   .venv\Scripts\python -m pip install -r requirements.txt
   ```
3. Crear tablas, catálogos mínimos (especies, largos) y el usuario `admin`:
   ```
   .venv\Scripts\python scripts\init_db.py
   ```
   Es idempotente: se puede volver a correr cuando se actualice `schema.sql`.
4. Arrancar: `run.bat` (o `.venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2`).
5. En el celular abrir `https://<servidor>/` (ver HTTPS abajo), ingresar como `admin`, cargar en **Catálogos** los contratistas y destinos reales, y aprobar los usuarios que se registren desde la app asignándoles rol y contratista.

Para dejarlo como servicio de Windows se recomienda [NSSM](https://nssm.cc/) apuntando a `run.bat`, o el Programador de tareas al iniciar el equipo.

### HTTPS (necesario para instalar la app y usarla sin conexión)

La app se abre y funciona por `http://`, pero el navegador sólo permite "Agregar a la pantalla de inicio" y la caché sin conexión de la pantalla (service worker) sobre HTTPS. Opciones, de más simple a más completa:

- **Caddy** como proxy inverso (recomendado): `caddy reverse-proxy --from logistica.pindo.local --to 127.0.0.1:8000 --internal-certs` y distribuir el certificado raíz de Caddy a los celulares (una vez). Con un dominio público, Caddy obtiene certificados válidos solos.
- **uvicorn con certificado propio**: agregar `--ssl-keyfile clave.pem --ssl-certfile cert.pem` al comando de `run.bat`.
- **IIS** con reescritura de URL hacia `127.0.0.1:8000`.

Si se accede por `http://` el servidor no debe tener `APP_ENV=prod` con HSTS; en ese caso la cola de envío sin conexión sigue funcionando (vive en `localStorage`), sólo falta la instalación como app.

## 2. Desarrollo y demo local

`.env` ya apunta al SQL Server 2012 Express local con la base `sapinfo` creada, las tablas aplicadas y los datos demo cargados. Para arrancar:

```
run.bat                                         -> http://localhost:8000  ·  documentación OpenAPI en /api/docs
```

Si hiciera falta recrear la base: `scripts\init_db.py` (tablas, catálogos mínimos, admin) y `scripts\seed_demo.py` (5 contratistas, 7 rodales, 35 tarifas, 8 camiones, usuarios por rol, 14 remitos, 6 días de histórico). `LF_ENV` elige qué archivo de entorno se carga (por defecto `.env`).

Usuarios demo (contraseña `Demo.2026`): `sup.ana` (supervisor y báscula), `elab.marcos` y `elab.lucia` (elaboradores), `transp.hector` y `transp.raul` (transportistas), `bascula.rosa`, `jefe.carlos` (Jefe de Área Forestal). `admin` / `Admin.2026`. Con `MODO_PRUEBA=true` (sólo dev) cualquier usuario entra a todos los roles.

`scripts\reset_demo.py` borra todo el contenido de las tablas `ZTLOGI_*` y vuelve a sembrar. Se niega si `APP_ENV=prod`.

## 3. Pruebas

```
.venv\Scripts\python -m pytest tests -q
```

- `test_reglas.py`: descuento de stock por circuito, avance de pedido (el exceso no compensa), tarifa por tracción, demoras y ciclos.
- `test_api.py`: contra la base local re-sembrada; recorre un día completo (disponibilidad, fila, inicio y fin de carga, báscula), programa, pedidos, tarifario con importación, remitos, PDF, registro y aprobación de usuarios, y los controles de permiso (supervisor sin tarifario, jefe en solo lectura, camiones y cargas ajenos). Corre con `MODO_PRUEBA=false` aunque el `.env` lo tenga activo.

## 4. Seguridad (resumen de lo implementado)

- Contraseñas con Argon2; bloqueo progresivo tras 5 intentos fallidos; JWT de acceso de 15 min y refresh de 30 días rotativo con detección de reutilización (se revoca toda la familia).
- Los usuarios nuevos quedan inactivos hasta que un administrador los aprueba y les asigna roles (`transportista`, `elaborador`, `supervisor`, `bascula`, `jefe`, `admin`) y, si corresponde, contratista.
- Toda autorización se decide en el servidor: por rol y por pertenencia (un transportista sólo opera sus camiones; un elaborador sólo su contratista; el supervisor no accede al tarifario; el Jefe de Área Forestal ve transporte y cosecha en solo lectura y recibe 403 si intenta escribir). El endpoint `/estado` devuelve a cada rol únicamente lo que le corresponde.
- Consultas SQL siempre parametrizadas (pyodbc). Validación de entrada con Pydantic y chequeos de dominio (horas, circuitos, catálogos activos, rangos).
- Fotos: límite 10 MB, verificación de que sea una imagen real (Pillow), re-codificación a JPEG, carpeta privada y enlaces firmados de 10 minutos.
- Cabeceras: CSP sin scripts externos, `X-Frame-Options`, `nosniff`, `Referrer-Policy`, HSTS en producción. Documentación OpenAPI desactivada en producción.
- Auditoría en `ZTLOGI_AUDITORIA` (antes/después, usuario, IP) de altas y bajas de camiones, aprobaciones, programa y emisiones, pedidos, finalización de cargas, tarifas, importaciones, remitos y cambios de usuarios.
- Lectura de remitos por IA: la clave vive sólo en el servidor, con límite diario por usuario y degradación a carga manual.

## 5. Operación

- **Cierres**: disponibilidad hasta `CIERRE_DISPONIBILIDAD` (20:00) y relevamiento hasta `CIERRE_RELEVAMIENTO` (21:00), siempre en hora de Argentina (`TZ`), validados en el servidor.
- **Sin conexión**: la app guarda la última instantánea y encola las acciones de campo (fila, estado, novedades, relevamiento, iniciar/finalizar carga, báscula, solicitudes, remitos con foto). Al volver la señal las envía en orden; si el servidor rechaza una (por ejemplo stock insuficiente porque otra carga se sincronizó antes) se descarta y se avisa. Las escrituras de supervisor, jefe y administrador exigen conexión.
- **Respaldo**: incluir `sapinfo` (tablas `ZTLOGI_*`) en el plan de backup diario de SQL Server y la carpeta `data/fotos/` en el backup de archivos.
- **Actualizar la app**: reemplazar la carpeta, `pip install -r requirements.txt`, `scripts\init_db.py` (aplica cambios de esquema idempotentes) y reiniciar. Subir `VERSION` en `static/sw.js` para que los celulares tomen la nueva versión.
- **Logs**: uvicorn escribe en consola; con NSSM se redirigen a archivo.

## 6. API

Base `/api/v1`, JSON, errores uniformes `{codigo, mensaje, detalle}`. Toda creación acepta un `id` UUID generado por el cliente y es idempotente. Rutas principales: `auth/*`, `me`, `usuarios` (admin), `catalogos/*`, `estado?rol=` (instantánea por rol), `camiones/*`, `pilas`, `programa/*`, `pedidos/*`, `cargas/*`, `bascula/*`, `rodales/*`, `tarifas/*` (importación `.xlsx`/`.csv`), `remitos/*`, `analisis`, `reportes/stock.pdf`, `camiones/{id}/reportes/fletes.pdf`. En desarrollo la referencia completa está en `/api/docs`.
