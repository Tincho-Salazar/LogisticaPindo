# Estado del desarrollo · 30/10/2026

Punto de continuación para la próxima sesión.

## Dónde estamos

- Backend y app móvil (PWA) **terminados, mejorados con trazabilidad punta a punta (Monte → Báscula → Remito) y rediseñados con UI/UX Pro Max**: tests de backend (`pytest`) y recorridos automatizados en navegador (`tests/ui/ui_walk.py`, `tests/ui/ui_flow.py`) en verde.
- **Mejoras implementadas**:
  - Cálculo de fletes por tonelada (`importe = round(tarifa_por_tonelada * toneladas)`).
  - Timestamp de dispositivo offline (`ocurrido_en`) respetado en relevamientos, cargas, fila, disponibilidad e incidencias.
  - Vinculación automática `carga_id` entre despachos de monte y remitos, pre-llenado inteligente del remito para el chofer, edición de remitos (`PUT /api/v1/remitos/{id}`), cálculo de ETA a báscula según km de asfalto/tierra, y tablero de **Trazabilidad y remitos** para el supervisor (sin exponer precios).
  - `backend/Caddyfile` listo para `correo.pindosa.com.ar` con TLS automático.
  - **Directiva Maestra UI/UX (31/10/2026)**: hoja "Pendientes de enviar" (tocar el chip de conexión o el aviso de pendientes) con la cola offline y los rechazos del servidor persistidos (`lf.fallas`, estado "error de sincronización"); importe estimado en vivo en el formulario de remito (tarifa × tn); bloqueo anti doble envío en todos los formularios; `confirm()` antes de quitar pila, remito, horario de báscula o camión del programa; chips de stock con conteo; botones con acción concreta; sin emojis.
  - **Interfaz igual a https://pindo-one.vercel.app/** (despliegue del mismo código con capa "Sistema de diseño v3"): se copió esa capa al final de `app.css`, el ícono SVG de Actualizar y las tipografías Inter + JetBrains Mono. Las fuentes se sirven desde `static/fonts/` (woff2 variables, locales: la CSP bloquea Google Fonts y el monte no tiene señal); el service worker pasó a `lf-v3` y cachea las fuentes.
  - **Administrador entra a todos los perfiles** (`roles_de` devuelve los 6 roles si tiene `admin`); en Transporte y Cosecha ve todos los camiones y contratistas en solo lectura, igual que el Jefe de Área Forestal (`es_jefe_puesto`). Los roles se refrescan en la sesión con cada `/estado`, sin re-login. Login y formularios (hojas) centrados vertical y horizontalmente en móvil y escritorio.
- **Todo corre en esta PC**: `backend/.env` apunta al SQL Server 2012 Express local (`.\SQLEXPRESS`, base `sapinfo`, autenticación de Windows) con las 30 tablas `ZTLOGI_*` creadas y datos demo cargados. Modo de prueba activo (cualquier usuario entra a todos los roles).
- **Producción (192.168.30.5\PRD) no se toca todavía.** La plantilla está en `backend/.env.prod` con credenciales vacías.
- No hay app Kotlin: el cliente móvil es la PWA (decisión del usuario: HTML5/CSS/JS sin frameworks). Queda ofrecida como segundo cliente si se quisiera.

## Cómo retomar

```
cd backend
run.bat                                   -> http://localhost:8000 (OpenAPI en /api/docs)
.venv\Scripts\python -m pytest tests -q   -> re-siembra la base local y corre todo
```
Usuarios demo (contraseña `Demo.2026`): `sup.ana`, `elab.marcos`, `elab.lucia`, `transp.hector`, `transp.raul`, `bascula.rosa`, `jefe.carlos`. Administrador: `admin` / `Admin.2026`.
Reseteo de datos demo: `.venv\Scripts\python scripts\reset_demo.py`.

Probar desde el celular (misma red): abrir el puerto una vez con
`netsh advfirewall firewall add rule name="Logistica Pindo 8000" dir=in action=allow protocol=TCP localport=8000`
y entrar a `http://192.168.30.100:8000` (cable) o `http://192.168.36.149:8000` (Wi-Fi). Instalar como app y caché sin señal requieren HTTPS (Caddy, ver `backend/README.md`).

## Pendientes (por orden sugerido)

1. Probar la app en un celular real (cámara de remitos, uso en campo) y ajustar lo que surja.
2. HTTPS con Caddy (o certificado propio) para poder instalarla y usarla sin señal.
3. Notificaciones push (Web Push con claves VAPID) y recordatorios 60 min antes de los cierres de 20:00 y 21:00.
4. Edición de un remito ya guardado (hoy: eliminar y volver a cargar).
5. Pantalla de control de remitos contra despachos para el supervisor (pendiente 19.9 del README).
6. Política de retención de fotos de remitos.
7. Pasar a producción: completar `.env.prod`, `copy .env.prod .env`, `scripts\init_db.py` contra `sapinfo` de 192.168.30.5, cargar catálogos reales e importar la planilla del tarifario.

## Mapa rápido del código

- `backend/app/reglas.py`: reglas de negocio puras (descuento de stock, avance de pedido, tarifa, demoras, ciclos).
- `backend/app/routers/estado.py`: instantánea por rol que consume la app (`GET /api/v1/estado?rol=`).
- `backend/app/routers/*.py`: un router por dominio; `consultas.py` tiene las consultas compartidas.
- `backend/static/`: `api.js` (sesión, llamadas, cola sin conexión), `util.js` (estado `S`/`ui` y helpers), `views.js` (pantallas), `sheets.js` (formularios), `app.js` (acciones y arranque), `sw.js` (caché de la cáscara).
- `backend/schema.sql`: esquema idempotente; los cambios se agregan al final con `IF NOT EXISTS`.
- `docs/DECISIONES.md`: decisiones tomadas frente al README original.
