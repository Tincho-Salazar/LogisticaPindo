# Decisiones de implementación

Registro de lo que se definió al construir la primera versión, en especial donde el pedido del usuario difiere de la especificación original (README.md) o donde ésta dejaba algo abierto (sección 19).

## Stack (pedido del usuario)

| Tema | README original | Implementado | Motivo |
|---|---|---|---|
| Base de datos | PostgreSQL 16 | **SQL Server 2012** `192.168.30.5\PRD`, base `sapinfo`, tablas con prefijo `ZTLOGI_` | Pedido explícito. El esquema (`schema.sql`) usa sólo sintaxis de 2012: índices filtrados, `DATETIME2`, `UNIQUEIDENTIFIER`, sin `DROP IF EXISTS`, `STRING_SPLIT` ni JSON nativo. Se validó contra un SQL Server 2012 Express local idéntico en versión. |
| Prefijo de tablas | — | `ZTLOGI_` (guion bajo) en lugar de `ZTLOGI-` | SQL Server exige corchetes para nombres con guion; el guion bajo identifica igual las tablas propias. |
| ORM y migraciones | SQLAlchemy + Alembic | `pyodbc` con SQL parametrizado y `schema.sql` idempotente aplicado por `scripts/init_db.py` | Menos dependencias, SQL transparente para quien administra `sapinfo`. Los cambios de esquema se agregan al final de `schema.sql` con `IF NOT EXISTS`. |
| App móvil | Android nativa (Kotlin, Compose, Room) | **PWA en HTML5/CSS/JavaScript puro** (sin Tailwind, Bootstrap ni frameworks) | Pedido explícito. Se instala desde el navegador, funciona sin conexión con `localStorage` + cola de envío + service worker. |
| Offline | Room + WorkManager | Instantánea del servidor en `localStorage`, outbox con UUID por operación, reenvío al reconectar | Mismo modelo (optimista + idempotente) con medios web. Las fotos de remitos sin conexión se guardan comprimidas en la cola. |
| Tareas en segundo plano | Celery + Redis | Ninguna: la lectura por IA es síncrona (≈ 5 s) dentro de la subida de la foto; los PDF se generan por demanda | Volumen bajo (decenas de remitos por día). Si crece, mover `ocr.leer_remito` a un hilo o cola. |
| Fotos | S3 / MinIO | Carpeta local `data/fotos/` con enlaces firmados (10 min) | Servidor propio; incluir la carpeta en el backup. |
| Notificaciones push | FCM | **No implementadas** en esta versión | Requieren proyecto Firebase o claves Web Push; la app refresca cada 30 s y al volver a primer plano. Web Push (VAPID) es el camino natural para la PWA. |
| Observabilidad | Prometheus, Sentry | Logs de uvicorn y tabla `ZTLOGI_AUDITORIA` | Suficiente para la escala inicial. |
| Pesaje | fuera de alcance | fuera de alcance | Igual que el README. |

## Modelo de datos y reglas

- **Horas**: se guardan en hora de Argentina (`DATETIME2(0)`, sin zona). Argentina no tiene horario de verano y el servidor y la base están en el país; se evita la conversión UTC en cada consulta. `TZ` en `.env` define la zona en Python (`zoneinfo` + `tzdata`).
- **Importes** enteros en pesos; **volúmenes** `DECIMAL(10,1)`; **toneladas** `DECIMAL(6,1)`.
- **Tarifa por tonelada (`tarifa * toneladas`)**: el importe de un remito se calcula como `round(tarifa_por_tonelada * toneladas)` según la tarifa vigente del par `(rodal, destino)` y la tracción del camión (`4x2` o `6x4`) a la fecha del remito. Se guarda tanto `tarifa_aplicada` (`$/tn` unitario) como `importe` total en `ZTLOGI_REMITOS`.
- **Trazabilidad Monte → Transporte → Báscula → Remito**: `ZTLOGI_REMITOS` incorpora `carga_id` vinculado automáticamente (o manualmente) a `ZTLOGI_CARGAS`. Cada despacho calcula además la **Hora Estimada de Llegada (ETA)** a báscula (`eta_bascula`) usando `km_asfalto` (60 km/h) y `km_tierra` (25 km/h) del tarifario vigente.
- **Timestamps de dispositivo offline (`ocurrido_en`)**: las operaciones de campo encoladas sin señal en el monte (`pilas`, `cargas`, `entrar-fila`, `disponibilidad-manana`, `incidencias`, `bascula`, `remitos`) envían la marca de tiempo real del teléfono (`ocurrido_en`), contra la cual el servidor valida los cierres de las 20:00 y 21:00 hs.
- **Historial de tarifas**: cambiar una tarifa cierra la anterior (`vigente_hasta = ayer`) y crea una nueva desde hoy; si la anterior empezó hoy y no tiene remitos asociados, se reemplaza (si ya tiene remitos, se conserva cerrada para preservar la integridad referencial). Los remitos conservan `tarifa_id`, `tarifa_aplicada` e `importe` calculados al guardarse o editarse (`PUT /api/v1/remitos/{id}`).
- **Relevamiento de stock**: se guarda por pila (crear/actualizar/quitar) con historial en `ZTLOGI_PILAS_HIST`; el "último relevamiento" por contratista es el máximo `relevado_en` de sus pilas. Cierre a las 21:00 validado en el servidor (409).
- **Empresas de transporte**: texto libre en camiones y usuarios (no hay tabla propia); alcanza para listar y filtrar.
- **Incidencias**: tabla con historial; a lo sumo una abierta por camión (abrir otra cierra la anterior). Una falla mecánica saca al camión de la fila.
- **Báscula**: el ingreso elige el camión y se asocia automáticamente a su última carga finalizada a industria sin ingreso (últimos 5 días); si no hay, se registra sin carga. Al registrar la salida un camión en ruta pasa a disponible.
- **Demoras de inicio**: se fija en `ZTLOGI_INICIOS_DIA` al iniciar la primera carga del día de cada contratista; la hora plan es la confirmada por el elaborador o, si no la marcó, la del primer camión programado.
- **Análisis**: se calculan en el servidor (`/analisis`, últimos 30 días) y se devuelven agregados; nunca se bajan miles de cargas al celular.
- **Jefe de Área Forestal**: roles `jefe` (tarifario, catálogos). Entra a Transporte y Cosecha en solo lectura (`solo_lectura` en la instantánea); el servidor rechaza sus escrituras porque no tiene los roles `transportista`/`elaborador`.
- **Escrituras del supervisor sin conexión** (pendiente 19.6): exigen conexión. Las de campo (transportista, elaborador, báscula) se encolan.
- **Rol admin** (pendiente 19.12): existe; `scripts/init_db.py` crea `admin` con la clave del `.env`. Aprueba usuarios, asigna roles y contratista, resetea contraseñas y administra catálogos.
- **Usuarios**: login por nombre de usuario (3 a 40 caracteres) y contraseña (pendiente 19.2). El registro deriva los roles sugeridos por tipo de empresa y puesto (sección 5.2) y queda inactivo hasta la aprobación.
- **Modo de prueba**: `MODO_PRUEBA=true` sólo tiene efecto si `APP_ENV` no es `prod`.
- **Transportista y tarifas**: en la instantánea se anula la columna de la tracción que no es la suya (sección 5.3).
- **Importación del tarifario**: destinos y empresas desconocidos se informan como error (hay que crearlos primero en catálogos con su circuito); los rodales nuevos se crean bajo la empresa indicada.

## Pendientes conocidos

- Notificaciones push (Web Push con VAPID) y recordatorios 60 min antes de los cierres.
- Edición de un remito ya guardado (hoy: eliminar y volver a cargar).
- Supervisión de remitos por el supervisor (pendiente 19.9).
- Política de retención de fotos (pendiente 19.11): hoy no se borran.
- Pruebas de carga con 200 usuarios (sección 17.1).
