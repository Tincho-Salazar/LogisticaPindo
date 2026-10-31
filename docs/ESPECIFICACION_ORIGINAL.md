# Logística Forestal Pindó SA — Especificación y prompt de desarrollo

Aplicación móvil Android (Kotlin) con backend en Python para coordinar el transporte de rollos de madera: relevamiento de stock en pila, programa de carga, despachos, báscula, pedidos de elaboración, tarifario de fletes y facturación de transportistas a partir de remitos.

> **Referencia funcional:** existe un prototipo navegable (una sola página HTML, datos de ejemplo, sin servidor) que ya implementa toda la lógica de pantallas descripta acá: https://claude.ai/artifact/L5z6fyEZVpQDkC94WtwANX
> El prototipo guarda todo en el navegador. Este documento describe cómo llevarlo a una aplicación real con base de datos central, usuarios, sincronización y funcionamiento sin conexión.

---

## Índice

1. [Prompt maestro para el agente de desarrollo](#1-prompt-maestro-para-el-agente-de-desarrollo)
2. [Alcance y objetivos](#2-alcance-y-objetivos)
3. [Stack tecnológico](#3-stack-tecnológico)
4. [Arquitectura](#4-arquitectura)
5. [Roles y permisos](#5-roles-y-permisos)
6. [Modelo de datos](#6-modelo-de-datos)
7. [Reglas de negocio](#7-reglas-de-negocio)
8. [Funcionalidades por rol (pantallas)](#8-funcionalidades-por-rol-pantallas)
9. [API REST del backend](#9-api-rest-del-backend)
10. [Modo sin conexión y sincronización](#10-modo-sin-conexión-y-sincronización)
11. [Lectura de remitos con foto (OCR)](#11-lectura-de-remitos-con-foto-ocr)
12. [Reportes PDF](#12-reportes-pdf)
13. [Notificaciones](#13-notificaciones)
14. [Seguridad, privacidad y auditoría](#14-seguridad-privacidad-y-auditoría)
15. [Requisitos no funcionales](#15-requisitos-no-funcionales)
16. [Estructura de repositorios y entornos](#16-estructura-de-repositorios-y-entornos)
17. [Pruebas y criterios de aceptación](#17-pruebas-y-criterios-de-aceptación)
18. [Plan de entrega por fases](#18-plan-de-entrega-por-fases)
19. [Decisiones y datos pendientes](#19-decisiones-y-datos-pendientes)
20. [Glosario](#20-glosario)

---

## 1. Prompt maestro para el agente de desarrollo

Copiar este bloque como instrucción inicial a un agente de desarrollo (o a un equipo). Las secciones 2 a 20 son el detalle al que remite.

```text
Sos un equipo senior de ingeniería de software. Tenés que construir "Logística Forestal Pindó SA",
una aplicación para coordinar el transporte de rollos de madera de una empresa forestal argentina.

ENTREGABLES
1. Backend en Python 3.12 con FastAPI, PostgreSQL 16, SQLAlchemy 2 + Alembic, Pydantic v2.
2. App móvil Android nativa en Kotlin con Jetpack Compose, arquitectura MVVM + Clean, Hilt,
   Retrofit/OkHttp, Room (offline-first), WorkManager, CameraX, Firebase Cloud Messaging.
3. Migraciones, datos semilla, colección de pruebas de la API, pipeline de CI y Docker Compose
   para desarrollo local.
4. Documentación de despliegue y runbook de operación.

CÓMO TRABAJAR
- Leé completo el README (secciones 2 a 19) antes de escribir código. Es la fuente de verdad.
- Trabajá por fases (sección 18). Al terminar cada fase: pruebas pasando, migraciones aplicadas,
  README de la fase actualizado y demo funcionando. No avances con pruebas rojas.
- Si algo no está definido o es ambiguo, anotalo en docs/DECISIONES.md con la opción elegida y
  el motivo; no frenes el avance salvo que cambie el modelo de datos de forma irreversible.
- No inventes datos reales: los destinos, rodales, tarifas y contratistas del README son de ejemplo y
  deben cargarse desde catálogos administrables (sección 6 y 19).
- Todo texto visible al usuario va en español rioplatense (es-AR), hora de Argentina
  (America/Argentina/Buenos_Aires), números con coma decimal y punto de miles, moneda en pesos ($).

REGLAS NO NEGOCIABLES
- El servidor es la autoridad de las reglas de negocio (stock, tarifas, cierres, permisos).
  El cliente móvil valida para dar buena experiencia, pero el backend vuelve a validar todo.
- Las operaciones del móvil son idempotentes: cada creación lleva un UUID generado en el cliente.
- Los permisos se aplican en el backend por rol y por pertenencia (un transportista solo ve
  sus camiones, un elaborador solo su contratista). Nunca confiar en filtros del cliente.
- La clave de la API de visión (lectura de remitos) vive solo en el servidor.
- Los importes se guardan como enteros en pesos (o Decimal), nunca como float. Los volúmenes
  como NUMERIC(10,1).
- Cada cambio de estado importante deja registro de auditoría (quién, cuándo, antes/después).
- Cobertura mínima de pruebas: 80 % en reglas de negocio del backend; pruebas de UI de los
  flujos críticos en Android.

DEFINICIÓN DE TERMINADO
Cada historia cumple sus criterios de aceptación (sección 17), tiene pruebas automáticas,
funciona sin conexión cuando la sección 10 lo exige y no rompe permisos (sección 5).
```

---

## 2. Alcance y objetivos

### 2.1 Problema

La empresa tiene contratistas de elaboración que cortan y apilan rollos en rodales (puntos de carga). Camiones de distintas empresas de transporte cargan esos rollos y los llevan a industrias propias (aserradero, planta de laminado) o a clientes de venta. Hoy el stock, el programa de carga, los horarios de báscula y los remitos se manejan por mensajes y planillas.

### 2.2 Objetivos

- Stock en pila actualizado por cada elaborador, visible para todos los que lo necesitan.
- Programa diario de carga (hoy y mañana) armado por el supervisor y visible para cada transportista y elaborador.
- Registro de cada carga y despacho, con rodal, circuito (industria o ventas) y destino.
- Control en báscula de ingreso y salida de cada camión, con histórico de horarios y tiempos.
- Pedidos de rollos por largo y categoría a cada contratista, con avance de cumplimiento descontado de los despachos.
- Tarifario de fletes por rodal, destino y tipo de camión, cargado únicamente por el Jefe de Área Forestal.
- Facturación del transportista calculada desde remitos fotografiados, con seguimiento mensual y reporte PDF.
- Análisis de rendimiento: ciclos de camiones, tiempos de carga, demoras de inicio.
- Funcionamiento sin conexión en el monte, con sincronización al recuperar señal.

### 2.3 Fuera de alcance de la primera versión

- Pesaje (peso bruto, tara y neto). Se retiró del prototipo a pedido; la báscula solo registra ingreso y salida.
- Facturación electrónica (ARCA/AFIP) y liquidación contable: el sistema calcula importes de control, no emite comprobantes.
- iOS.
- Integración con GPS o telemetría de camiones.

---

## 3. Stack tecnológico

### 3.1 Backend (Python)

| Componente | Elección | Notas |
|---|---|---|
| Lenguaje | Python 3.12 | Tipado estricto con `mypy`. |
| Framework web | FastAPI | OpenAPI generado automáticamente. |
| ASGI | Uvicorn detrás de Gunicorn | `--workers` según CPU. |
| Base de datos | PostgreSQL 16 | Extensiones `pgcrypto` o `uuid-ossp`, `pg_trgm`. |
| ORM y migraciones | SQLAlchemy 2.x + Alembic | Migraciones versionadas, nunca editar una ya aplicada. |
| Validación | Pydantic v2 | Esquemas de entrada y salida separados de los modelos. |
| Autenticación | JWT (access 15 min, refresh 30 días rotativo) | `passlib[argon2]` para contraseñas. |
| Tareas en segundo plano | Celery + Redis (o ARQ) | OCR de remitos, PDF pesados, notificaciones. |
| Almacenamiento de archivos | S3 compatible (MinIO en desarrollo) | Fotos de remitos. URLs firmadas de corta duración. |
| PDF | ReportLab (o WeasyPrint) | Reportes de stock y de fletes. |
| Notificaciones push | Firebase Cloud Messaging (FCM) HTTP v1 | Token por dispositivo. |
| Visión por IA | SDK oficial de Anthropic (`anthropic`) | Modelo configurable por variable de entorno. |
| Planificador | APScheduler o Celery beat | Cierres diarios, recordatorios. |
| Observabilidad | Logs JSON, Prometheus, Sentry | Trazas con `request_id`. |
| Calidad | `ruff`, `black`, `mypy`, `pytest`, `pytest-asyncio`, `factory-boy`, `testcontainers` | CI obligatorio. |
| Contenedores | Docker y Docker Compose | Servicios: api, worker, db, redis, minio. |

### 3.2 App móvil (Kotlin / Android)

| Componente | Elección | Notas |
|---|---|---|
| Lenguaje | Kotlin 2.x | Coroutines y Flow. |
| UI | Jetpack Compose + Material 3 | Tema claro y oscuro. Área táctil mínima 48 dp. |
| Arquitectura | MVVM + Clean (data / domain / ui) | Un módulo Gradle por capa o por feature. |
| Inyección | Hilt | |
| Red | Retrofit + OkHttp + kotlinx.serialization | Interceptor de autenticación y refresco de token. |
| Base local | Room | Fuente de verdad de la UI (offline-first). |
| Sincronización | WorkManager | Cola de salida (outbox) y descarga incremental. |
| Cámara | CameraX | Captura de remitos con compresión previa. |
| Imágenes | Coil | Miniaturas con caché. |
| Navegación | Navigation Compose | Un grafo por rol. |
| Notificaciones | FCM | Canal por tipo de aviso. |
| PDF | Descarga del PDF generado por el backend, apertura con `FileProvider` y `Intent.ACTION_VIEW` | |
| Seguridad | `EncryptedSharedPreferences` / Android Keystore para tokens | Bloqueo opcional con biometría. |
| Versiones | `minSdk 26` (Android 8.0), `targetSdk` vigente | |
| Calidad | ktlint, detekt, JUnit5, MockK, Turbine, Compose UI Test, Room in-memory | |

### 3.3 Distribución

- Primera etapa: APK/AAB firmado, distribución interna (Firebase App Distribution o enlace directo).
- Segunda etapa: Google Play (pista cerrada de pruebas y luego producción).
- Actualización forzada: el backend expone `GET /app/version` con `min_supported_version`; la app bloquea el uso si es menor.

---

## 4. Arquitectura

```
┌────────────────────────────┐        HTTPS / JSON        ┌───────────────────────────────┐
│   App Android (Kotlin)     │ ◄────────────────────────► │   API FastAPI (Python)        │
│  Compose · Room · WorkMgr  │   JWT · idempotencia       │  routers · servicios · repos  │
│  CameraX · FCM             │                            └──────┬─────────┬──────────┬───┘
└────────────────────────────┘                                   │         │          │
                                                          PostgreSQL     Redis     S3/MinIO
                                                                           │          (fotos)
                                                                      Celery worker
                                                              (OCR remitos · PDF · push · cierres)
                                                                           │
                                                                  API de visión (Anthropic)
```

### 4.1 Capas del backend

```
app/
  api/            routers por dominio (auth, camiones, stock, programa, cargas, bascula, pedidos,
                  tarifas, remitos, analisis, reportes, sync, catalogos)
  core/           config, seguridad, dependencias, errores, zona horaria
  domain/         reglas de negocio puras (sin I/O): stock, programa, tarifas, ciclos, avance de pedido
  services/       casos de uso que orquestan repositorios y reglas
  repositories/   acceso a datos (SQLAlchemy)
  models/         modelos ORM
  schemas/        esquemas Pydantic (request / response)
  workers/        tareas Celery
  reports/        generación de PDF
tests/            unitarias (domain), integración (api + db), contrato
alembic/          migraciones
```

### 4.2 Principios

- **Reglas en `domain/`**: funciones puras y testeables (cálculo de avance de pedido, importe de un remito, demora de inicio, descuento de stock).
- **Jornada operativa**: toda regla de "hoy" y "mañana" usa la fecha en `America/Argentina/Buenos_Aires`, nunca UTC. Las marcas de tiempo se guardan en UTC (`timestamptz`).
- **Catálogos administrables** (destinos, contratistas, rodales, especies, largos): no deben estar escritos en el código.
- **Soft delete** para camiones, rodales y destinos (historial intacto).

---

## 5. Roles y permisos

Roles de la aplicación: `transportista`, `elaborador`, `supervisor`, `bascula`, `jefe_area_forestal`. Se recomienda sumar `admin` (alta de usuarios y catálogos) aunque el prototipo no lo tenga.

### 5.1 Alta de usuario

Al primer ingreso el usuario completa (el prototipo ya lo hace):

- Nombre y apellido.
- Empresa a la que pertenece.
- Tipo de empresa: `Transporte`, `Elaborador`, `Pindó SA`.
- Puesto: `Capataz`, `Mecánico`, `Maquinista`, `Chofer`, `Supervisor`, `Jefe de Área Forestal`, `Otro`.

En producción el rol efectivo lo asigna un administrador o se deriva de tipo de empresa y puesto. Hay un interruptor de configuración equivalente al `MODO_PRUEBA` del prototipo (un usuario con acceso a todo) que **debe estar apagado en producción** y solo habilitarse en entornos de prueba.

### 5.2 Reglas de acceso por rubro (producción)

| Tipo de empresa | Puesto | Roles habilitados |
|---|---|---|
| Transporte | cualquiera | `transportista` |
| Elaborador | cualquiera | `elaborador` (solo su contratista) |
| Pindó SA | Supervisor | `supervisor`, `bascula` |
| Pindó SA | Jefe de Área Forestal | `jefe_area_forestal` (más lectura de transporte y cosecha) |
| Pindó SA | otros | `bascula` |

### 5.3 Matriz de permisos

L = leer, E = escribir (crear/editar/borrar según el caso), — = sin acceso. "Propio" = solo sus datos.

| Recurso | Transportista | Elaborador | Supervisor | Báscula | Jefe Área Forestal |
|---|---|---|---|---|---|
| Stock en pila | — | E propio | L todo | — | L (panel cosecha) |
| Camiones (alta/edición/baja) | E propio (alta pendiente) | — | E todo, aprueba altas | L | L (panel transporte) |
| Disponibilidad para mañana | E propio | — | L | — | L |
| Programa de carga | L propio | L propio frente | E | — | L |
| Prioridad de carga por frente | L | L | E | — | L |
| Unidades mínimas solicitadas | — | E propio | L | — | L |
| Hora de inicio de carga | L | E propio | L | — | L |
| Pedido de rollos | — | L propio | E | — | L |
| Cargas (iniciar/finalizar) | — | E propio | L | — | L |
| Aviso de descarga (ventas) | E propio | — | L | — | — |
| Báscula (ingreso/salida) | — | — | L | E | — |
| Horarios y descansos de báscula | L | — | L | E | — |
| Rodales y tarifario | L propio (solo su tracción) | — | **sin acceso** | — | **E** |
| Remitos de flete | E propio | — | — | — | L (panel transporte, solo lectura) |
| Facturación propia y reporte PDF | L propio | — | — | — | — |
| Análisis de rendimiento | — | — | L | — | — |
| Reporte PDF de stock | — | — | L | — | — |
| Catálogos (destinos, contratistas) | — | — | L | — | E |
| Usuarios | — | — | — | — | — (solo `admin`) |

**Regla clave:** el supervisor **no** accede a nada del tarifario. El Jefe de Área Forestal es el único que imputa tarifas y rodales. En los paneles de transporte y cosecha el jefe entra en **solo lectura**: la API rechaza con `403` cualquier escritura suya sobre esos recursos, y la app oculta los botones de edición.

---

## 6. Modelo de datos

Convenciones: `id` UUID (v4 o v7) generado por el cliente cuando nace offline; `created_at`, `updated_at`, `deleted_at` (timestamptz); `created_by` y `updated_by` (FK a `usuarios`); `version` entero para control optimista. Se omiten en las tablas por brevedad.

### 6.1 Catálogos

**`contratistas`** (empresas de elaboración): `nombre` (único), `activo`.

**`empresas_transporte`**: `nombre`, `cuit` (opcional), `activo`.

**`destinos`**: `nombre` (único), `circuito` (`industria` | `ventas`), `activo`.
Ejemplo: Aserradero propio y Planta de laminado (industria); Cliente Litoral, Cliente Norte, Exportación (puerto) (ventas). En la planilla real del tarifario aparecen, entre otros, FE, GYV, PINDÓ SA, PINDÓ SA (Mado), PINDÓ SA (Delicia), ZAVALA MAD SRL, EST. IMHOF: **cargarlos desde este catálogo, no escribirlos en el código.**

**`especies`**: `nombre` (Pino Taeda, Pino Híbrido, Eucaliptus, Araucaria).

**`largos`**: `pies` (8, 10, 12, 14, 16, 18, 20). Configurable.

**`rodales`** (puntos de carga): `codigo` (único, mayúsculas sin espacios, p. ej. `MMA07XC073`), `contratista_id`, `activo`.

### 6.2 Usuarios y dispositivos

**`usuarios`**: `nombre_apellido`, `email` o `telefono` (login), `password_hash`, `empresa`, `tipo_empresa` (`transporte`|`elaborador`|`pindo`), `puesto`, `roles[]`, `contratista_id` (si es elaborador), `activo`.

**`dispositivos`**: `usuario_id`, `fcm_token`, `modelo`, `version_app`, `ultimo_acceso`.

### 6.3 Camiones

**`camiones`**: `patente` (única entre no eliminados, normalizada sin espacios), `chofer`, `telefono`, `empresa_transporte_id`, `capacidad_tn` (NUMERIC 5,1), `traccion` (`4x2` | `6x4`), `tara_kg` (opcional), `estado` (`disponible` | `fila` | `cargando` | `ruta` | `vacio`), `alta_estado` (`pendiente` | `aprobada` | `rechazada`), `alta_hora`, `alta_por`, `fila_desde`, `fila_contratista_id`, `baja` (bool), `propietario_usuario_id`.

**`incidencias`**: `camion_id`, `tipo` (`mecanico` | `demora`), `motivo` (lista: Neumático, Frenos, Motor, Sistema eléctrico, Acoplado o pluma, Espera en balanza, Espera para descargar, Ruta o camino cortado, Clima, Documentación, Otro), `detalle`, `desde`, `resuelta_en`.

**`disponibilidad_manana`**: `camion_id`, `fecha_jornada` (la del día para el que responde), `valor` (`si`|`no`), `respondida_en`. Única por camión y jornada. Se puede cambiar hasta el cierre (20:00).

### 6.4 Stock

**`relevamientos_stock`** (encabezado): `contratista_id`, `jornada`, `relevado_por`, `relevado_en`.

**`pilas`**: `contratista_id`, `especie_id`, `tipo` (`fino` | `grueso`), `largo_pies`, `volumen_m3` (NUMERIC 10,1), `uso` (`pindo` | `ventas`), `relevado_en`, `relevado_por`.

Reglas: por contratista **solo vale el último relevamiento**; el nuevo reemplaza el anterior (se conserva histórico para análisis en `pilas_historial`). El prototipo ya no registra rodal en el relevamiento de pilas.

"Stock Pindó SA" (uso `pindo`) y "Stock de ventas" (uso `ventas`) se muestran por separado.

### 6.5 Programa de carga

**`programa_items`**: `jornada` (fecha), `camion_id`, `contratista_id`, `hora` (hora de carga del camión), `estado` (`programado` | `cargando` | `cumplido` | `quitado`), `orden`.

**`programa_emisiones`**: `jornada`, `emitido_por`, `emitido_en`. Si no hay emisión para mañana, los transportistas no ven asignación.

**`prioridad_frente`**: `jornada`, `contratista_id`, `prioridad` (`ninguna` | `pindo` | `ventas`). Solo se puede fijar para mañana cuando el contratista ya confirmó stock.

**`solicitudes_unidades`**: `jornada`, `contratista_id`, `cantidad_minima` (1 a 99), `nota`, `solicitada_por`, `solicitada_en`.

**`inicio_carga_confirmado`**: `jornada`, `contratista_id`, `hora`, `marcado_por`, `marcado_en` (lo carga el elaborador).

### 6.6 Pedidos de rollos

**`pedidos`**: `contratista_id`, `jornada`, `nota`, `creado_por`, `creado_en`, `desde` (fecha desde la que se cuentan despachos).

**`pedido_lineas`**: `pedido_id`, `tipo` (`fino` | `grueso`), `largo_pies`, `volumen_m3`.

Avance (se calcula, no se guarda): ver sección 7.4.

### 6.7 Cargas y despachos

**`cargas`**: `camion_id`, `contratista_id`, `rodal_id`, `programa_item_id`, `circuito` (`industria` | `ventas`, se define al finalizar), `destino_id`, `estado` (`en_curso` | `finalizada`), `inicio_en`, `fin_en`, `espera_min` (tiempo en fila antes de cargar), `retorno_en` (cuando el camión vuelve a entrar en fila), `jornada`, `operador_id`.

**`carga_lineas`**: `carga_id`, `pila_id` (origen, opcional), `tipo`, `largo_pies`, `volumen_m3`.

### 6.8 Báscula

**`bascula_movimientos`**: `carga_id`, `camion_id`, `ingreso_en`, `salida_en`, `operador_id`.

**`bascula_turnos`**: `desde`, `hasta` (franjas de atención disponibles). **`bascula_descansos`**: `desde`, `hasta`, `motivo`.

El transportista ve ambos en la parte superior de "Mi viaje".

### 6.9 Tarifario, remitos y facturación

**`tarifas`**: `rodal_id`, `destino_id`, `km_asfalto` (NUMERIC 6,1), `km_tierra` (NUMERIC 6,1), `tarifa_4x2` (entero, pesos), `tarifa_6x4` (entero, pesos), `vigente_desde`, `vigente_hasta` (nulo = vigente). Única por (`rodal_id`, `destino_id`, `vigente_desde`). **Conservar el historial de tarifas** y calcular cada remito con la tarifa vigente en la fecha del remito.

La planilla de origen tiene estas columnas: Empresa, Rodal, Destino, Km asfalto, Km tierra, 4x2, 6x4. Debe poder importarse (sección 9.10).

**`remitos`**: `camion_id`, `numero`, `fecha`, `rodal_id`, `destino_id` (opcional), `toneladas` (NUMERIC 6,1), `foto_key` (objeto en S3), `foto_miniatura_key`, `origen_dato` (`ocr` | `manual`), `ocr_json` (respuesta cruda), `estado_ocr` (`pendiente` | `leido` | `fallido`), `tarifa_aplicada` (entero), `tarifa_id`, `importe` (entero), `cargado_por`, `cargado_en`. Único por (`camion_id`, `numero`) cuando `numero` no es vacío.

El `importe` se calcula al guardar (y se recalcula si cambian rodal, destino o la tarifa vigente) con la regla de 7.6.

### 6.10 Análisis (derivados)

Se calculan con consultas o vistas materializadas sobre `cargas`, `bascula_movimientos` y `inicio_carga_confirmado`. No se guardan como tablas operativas.

### 6.11 Auditoría y sincronización

**`auditoria`**: `entidad`, `entidad_id`, `accion`, `antes` (jsonb), `despues` (jsonb), `usuario_id`, `en`, `ip`.

**`sync_cambios`** (opcional, para el feed incremental): `entidad`, `entidad_id`, `operacion` (`upsert` | `delete`), `cambiado_en` (con índice), `ambito` (contratista, camión, global).

---

## 7. Reglas de negocio

### 7.1 Relevamiento de stock

- Solo el elaborador de ese contratista (y el supervisor por excepción documentada) puede relevar.
- El relevamiento de una jornada **cierra a las 21:00** (configurable `CIERRE_RELEVAMIENTO`). Después de la hora el elaborador no puede modificarlo; la pantalla muestra el estado "cerrado".
- Se registra quién relevó y a qué hora. Las pantallas del supervisor muestran, por contratista, el **último relevamiento (hora y nombre)** y se actualizan solas.
- Un nuevo relevamiento reemplaza al anterior para ese contratista.
- Volumen en m³ con un decimal. Debe ser mayor que cero.

### 7.2 Camiones y altas

- El transportista da de alta su camión (patente, chofer, teléfono, empresa, capacidad, **tracción 4x2 o 6x4**). Queda `alta_estado = pendiente`.
- El supervisor aprueba o rechaza. Mientras está pendiente, el transportista solo ve una pantalla de "alta en revisión" y no puede usar la app.
- El supervisor también puede dar de alta camiones, editarlos y eliminarlos (baja lógica). Un camión en estado `cargando` no se puede eliminar.
- La lista de camiones del supervisor muestra solo camiones aprobados y no eliminados. Las altas pendientes se muestran aparte con botones aprobar y rechazar.
- Patente única entre camiones activos (comparación sin espacios, mayúsculas).
- Cuando un transportista inicia sesión, elige entre **sus** camiones (los que dio de alta o donde figura como chofer).

### 7.3 Programa de carga

- El supervisor arma el programa de **hoy** y de **mañana**: por cada contratista, tilda los camiones asignados y fija la hora de carga.
- Cada camión puede estar en una sola asignación activa por jornada.
- Para mañana, el supervisor ve el resumen de disponibilidad: disponibles, no disponibles y sin respuesta, con la lista de cada grupo.
- **Prioridad de carga** por frente (`ninguna`, `Stock Pindó SA`, `Ventas`): solo se habilita para mañana cuando el contratista ya confirmó su stock. Se muestra junto al stock disponible de cada tipo.
- **Emisión**: el supervisor emite el programa; recién entonces transportistas y elaboradores ven su asignación. Puede reemitirse.
- El elaborador puede solicitar una **cantidad mínima de unidades** para mañana; el supervisor ve lo solicitado contra lo programado y se marcan los frentes con menos camiones que los solicitados.
- El elaborador marca la **hora de inicio de carga** de mañana. Esa hora es la que ven transportistas y supervisor como "inicio de carga del frente". Si no la marca, se usa la hora del primer camión asignado.
- Disponibilidad: el transportista responde si estará disponible para el programa del día siguiente **hasta las 20:00** (configurable `CIERRE_DISPONIBILIDAD`). Puede cambiar su respuesta hasta esa hora.
- El transportista ve **solo su** asignación, con pestañas **Hoy** y **Mañana**: hora, inicio de carga del frente, posición en la cola, prioridad del frente y stock de Pindó SA y de ventas disponible para mañana.

### 7.4 Pedido de rollos y avance de cumplimiento

- El **supervisor** carga, por contratista, un pedido con líneas (`tipo` fino/grueso, `largo`, `m³`) y una nota. El elaborador lo ve en su pestaña "Pedido".
- **Despachado por línea** = suma de `carga_lineas.volumen_m3` de cargas **finalizadas** del contratista, del mismo tipo y largo, con `jornada >= pedido.desde`.
- **Avance de la línea** = `min(100 %, despachado / pedido)`.
- **Cumplimiento general** = `suma(min(despachado_i, pedido_i)) / suma(pedido_i)`. El exceso de una línea **no compensa** a otra.
- Lo despachado de largos o categorías que no están en el pedido se informa aparte y no suma.
- El elaborador compara además contra su **stock en pila** y se marca en rojo lo que falta y no alcanza.
- Al modificar un pedido, `desde` se conserva (el avance no se reinicia).

### 7.5 Cargas y despachos

- Una carga empieza cuando el elaborador inicia la carga de un camión programado (`en_curso`; el camión pasa a `cargando`). Se registra `inicio_en` y, si venía de la fila, el `espera_min`.
- Al **finalizar** el elaborador/operador de grúa indica:
  1. **Circuito**: `industria` o `ventas`.
  2. **Rodal de carga** (entre los rodales del contratista).
  3. **Líneas**: tipo fino/grueso, largo y m³ de cada una.
  4. **Destino** (los de ese circuito).
- Validaciones del servidor: volumen > 0; no superar el stock disponible por tipo y largo; rodal pertenece al contratista; destino pertenece al circuito.
- **Descuento de stock** al finalizar: se descuentan las pilas del contratista del mismo tipo y largo. En circuito `industria` se consumen primero las pilas de uso `pindo` y nunca las de ventas. En circuito `ventas` se consumen primero las pilas de uso `ventas`.
- El camión pasa a estado `ruta` (cargado). La asignación del programa pasa a `cumplido`.
- Si el finalizar se hizo sin conexión y el servidor lo rechaza por stock insuficiente, la app muestra un conflicto para corregir (sección 10.4).

### 7.6 Ciclo del camión

- **Salida del punto de carga** = fin de la carga (`fin_en`).
- **Retorno al punto de carga** = momento en que el camión entra en la fila de espera de un frente (acción "entrar en fila"). Se guarda en `retorno_en` de la última carga abierta.
- **Duración del ciclo** = `retorno_en − fin_en`. Se descartan ciclos mayores a 1000 minutos o sin retorno.
- El transportista no puede entrar en fila si tiene una incidencia mecánica abierta ni sin asignación.

### 7.7 Descarga y estados del camión

- **Industria propia**: la descarga la maneja la báscula. Al registrar la **salida** de báscula el camión pasa a `disponible` automáticamente. El transportista no tiene botones de aviso de descarga para estas cargas.
- **Ventas**: el transportista puede avisar "descargué" y "disponible" **solo si su última carga fue a ventas**. En cualquier otro caso esos botones no están.
- Incidencias: el transportista puede reportar falla mecánica o demora con motivo. La falla mecánica lo saca de la fila y del programa disponible.

### 7.8 Báscula

- **Ingreso**: el operador elige el camión en una lista desplegable de los camiones dados de alta y aprobados (solo la patente; sin detalle de lo que transporta). Se registra `ingreso_en`. El camión queda en "Descargando en planta".
- **Salida**: botón "Registrar salida" sobre cada camión descargando. Se registra `salida_en`.
- **Visores**:
  - Ingresos y salidas del día con contadores.
  - Camiones cargados con destino a industria (por descargar y total del día), con el número de camiones.
- **Histórico y estimaciones**:
  - Horarios pico de ingreso (histograma por hora).
  - Promedio de tiempo de descarga por día y por camión (`salida − ingreso`).
- **Horarios de báscula**: el operador carga turnos disponibles y descansos programados. Los transportistas los ven arriba de "Mi viaje", con el estado actual (abierta / en descanso / cerrada).

### 7.9 Tarifario (solo Jefe de Área Forestal)

- El jefe carga **rodales** (código y contratista) y, por cada rodal, **destinos** con km de asfalto, km de tierra, tarifa 4x2 y tarifa 6x4 en pesos.
- Para cada par (rodal, destino) hay una sola tarifa vigente. Al cambiarla se cierra la anterior (`vigente_hasta`) y se crea una nueva; los remitos viejos conservan la tarifa con la que se calcularon.
- Debe poder **importarse desde Excel/CSV** con las columnas de la planilla (sección 9.10), con vista previa de errores antes de confirmar.
- El supervisor **no ve ni edita** nada de tarifas.

### 7.10 Remitos y facturación del transportista

- Cada remito vale una tarifa: `tarifa(rodal, destino, traccion_del_camion)` vigente en la fecha del remito.
  - Si el remito no tiene destino o no existe tarifa para ese par, el importe queda **sin tarifa** y no suma a la facturación. Se avisa al transportista.
- Un remito exige: rodal y toneladas (> 0). Destino, número y fecha son opcionales aunque se recomienda cargarlos. El número no puede repetirse para el mismo camión.
- **Facturación mensual** = suma de importes de los remitos del mes calendario.
- **Acumulado del mes por carga**: en la lista, cada remito muestra el acumulado del mes hasta esa carga (orden por fecha y hora).
- **Seguimiento**: últimos 6 meses, con cantidad de remitos, toneladas, facturación y variación contra el mes anterior. No hay vista semanal.
- **Toneladas por rodal**: tabla del mes con remitos, toneladas y facturación por rodal.
- **Control de despachos contra remitos**: si en el mes hay más despachos finalizados del camión que remitos cargados, se avisa cuántos remitos faltan escanear.
- **Reporte PDF** (sección 12.2).

### 7.11 Análisis de rendimiento (supervisor)

Todos los análisis aceptan filtro por circuito (`todos`, `industria`, `ventas`) salvo "Demoras de inicio".

1. **Ciclos por punto de carga**: promedio, mínimo, máximo, cantidad de ciclos, cantidad de camiones, espera promedio en carga, diferencia contra el promedio general (verde si es menor a −10 min, rojo si supera +10 min).
2. **Ciclos por industria y destino**: igual, agrupado por destino, con el circuito.
3. **Cruce punto de carga × destino**: matriz con el promedio de ciclo; rojo en el 25 % más lento, verde en el 25 % más rápido.
4. **Ranking de transportistas**: por camión, con patente y chofer.
5. **Tiempos de carga**: `fin_en − inicio_en` por carga; promedio general, cargas de hoy con diferencia contra el promedio, y promedio por punto de carga. *(El seguimiento por camión se retiró por pedido.)*
6. **Demoras de inicio**: por contratista, `primer inicio real del día − hora de inicio confirmada por el elaborador` (si no hay confirmación se usa la hora programada y se marca como tal). Hasta **5 minutos** es "a horario"; iniciar antes no cuenta como demora. Muestra demora promedio general, porcentaje a horario, ranking por contratista y el detalle de hoy.

### 7.12 Cierres automáticos

- 20:00: se cierra la respuesta de disponibilidad para mañana.
- 21:00: se cierra el relevamiento de stock del día.
- Ambos horarios son configurables y se leen siempre en hora de Argentina.

---

## 8. Funcionalidades por rol (pantallas)

La barra superior de todos los roles muestra: estado de conexión, hora del último dato, botón **Actualizar** y el rol activo con opción de cambiarlo. Además de la actualización manual, la app refresca cada 30 segundos y al volver a primer plano.

### 8.1 Transportista

Navegación: **Mi viaje**, **Programa**, **Fletes**.

- **Mi viaje**
  - Arriba: horarios de báscula (turnos y descansos) y estado actual.
  - Estado del camión, asignación vigente, posición en la cola.
  - Acciones: entrar en fila, salir de fila, reportar falla mecánica o demora, resolver incidencia.
  - Aviso de descarga y disponibilidad (solo si la última carga fue a ventas).
  - **Disponibilidad para el programa de mañana** (sí/no) hasta las 20:00.
- **Programa**
  - Chips Hoy / Mañana. Solo su asignación: hora, inicio de carga del frente, posición en cola, prioridad del frente, stock Pindó SA y de ventas para mañana.
- **Fletes**
  - Resumen del mes: facturado, acumulado general, cantidad de remitos, tracción del camión.
  - Botón **Descargar reporte PDF**.
  - Avisos de control (remitos sin tarifa, remitos faltantes frente a despachos).
  - **Seguimiento de facturación por mes** (6 meses, barras, variación).
  - **Remitos y facturación por carga**: botón **Escanear remito con la cámara**; tabla del mes por rodal; lista de remitos con miniatura, número, rodal → destino, fecha, toneladas, acumulado del mes e importe. Al tocar uno: foto grande, importe y opción eliminar.
  - **Tarifas por rodal y destino**: tabla con km de asfalto, km de tierra y columnas 4x2 / 6x4, resaltando la de su camión.
- Pantalla previa de selección de camión (solo los propios) y de **alta de camión** si no tiene.

### 8.2 Elaborador

Navegación: **Mi stock**, **Cola de carga**, **Programa**, **Pedido**.

- **Mi stock**: relevamiento por tipo (fino/grueso), largo, especie y m³, con "Stock Pindó SA" y "Stock de ventas" por separado. Sin campo de rodal. Estado de cierre (21:00). Quién y cuándo relevó.
- **Cola de carga**: camiones en fila, en carga y cargas finalizadas del día. Acciones: iniciar carga, finalizar carga (circuito, **rodal de carga**, líneas fino/grueso con largo y m³, destino).
- **Programa**
  - Tarjeta **Hora de inicio de carga** de mañana (marcar, modificar, quitar).
  - Tarjeta **Unidades mínimas necesarias** (cantidad y detalle).
  - Programa asignado y emitido: camiones, capacidad total, inicio de carga, alerta si faltan unidades.
- **Pedido**: cumplimiento general (porcentaje y barra, m³ enviados de m³ pedidos, faltante), reparto fino/grueso, indicación del supervisor, tabla por largo y categoría con pedido, enviado, avance y stock en pila.

### 8.3 Supervisor

Navegación: **Stock**, **Camiones**, **Programa**, **Pedidos**, **Análisis**. (No tiene Tarifas ni Cargas.)

- **Stock**: pilas por contratista con último relevamiento (hora y nombre), filtros fino/grueso, vista de "Stock Pindó SA" y "Stock de ventas", botón de **reporte PDF de stock**.
- **Camiones**: lista de camiones aprobados con filtro por estado, novedades, resumen de disponibilidad de mañana, altas pendientes con aprobar/rechazar, alta/edición/baja.
- **Programa** (Hoy/Mañana): constructor con acordeón por contratista (tildar camiones, hora por contratista), prioridad de carga por frente (mañana, tras confirmación de stock), inicio de carga del frente, unidades solicitadas, emisión y reemisión.
- **Pedidos**: una tarjeta por contratista con cumplimiento (porcentaje, barra, tabla por largo y categoría con pedido, enviado, avance, indicación, quién y cuándo); botón **Asignar/Modificar pedido**.
- **Análisis**: vistas de la sección 7.11 con filtro de circuito.

### 8.4 Báscula

Navegación: **Báscula**, **A industria**, **Horarios**.

- **Báscula**: selector de camión, **Registrar ingreso**, tarjetas "Descargando en planta" con **Registrar salida**, listado de ingresos y salidas del día y contadores.
- **A industria**: visor y contador de camiones cargados con destino a industria.
- **Horarios**: alta y baja de turnos y descansos; histograma de ingresos por hora; promedio de descarga por día y por camión.

### 8.5 Jefe de Área Forestal

Al iniciar, el jefe elige una de tres entradas:

- **Tarifario** (edición): rodales (+ Rodal, quitar) y por rodal sus destinos con km y tarifas (+ Destino, editar, quitar); importación desde planilla.
- **Transporte** (solo lectura): elige un camión y ve su panel (Mi viaje, Programa, Fletes).
- **Cosecha** (solo lectura): elige un contratista y ve su panel (Mi stock, Cola de carga, Programa, Pedido).

En solo lectura se ve un aviso fijo "Vista de solo lectura", no hay botones de acción y el backend responde `403` a cualquier escritura.

### 8.6 Criterios de interfaz comunes

- Compose + Material 3, tema claro y oscuro, tipografía legible al sol (contraste alto, números grandes).
- Todas las acciones táctiles ≥ 48 dp. Estados vacíos con texto claro y siguiente paso.
- Formato de fecha `dd/mm`, hora `HH:mm`, volumen `27,4 m³`, importe `$ 105.800`.
- Errores de red no bloquean: la acción queda en cola y se muestra "pendiente de enviar".
- Accesibilidad: `contentDescription` en iconos, no depender solo del color (siempre texto o icono), soporte de fuente grande.

---

## 9. API REST del backend

Base: `/api/v1`. Formato JSON UTF-8. Fechas ISO 8601 con zona. Errores con cuerpo uniforme `{ "codigo": "...", "mensaje": "...", "detalle": {...} }`. Paginación por cursor en listados largos. Todos los `POST` de creación aceptan el `id` generado por el cliente y son **idempotentes** (reintentar devuelve el mismo recurso, `200` en lugar de `201`).

### 9.1 Autenticación y perfil

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/auth/registro` | Alta de usuario (nombre, empresa, tipo, puesto, credenciales). Queda a la espera de aprobación del rol. |
| POST | `/auth/login` | Devuelve `access_token` y `refresh_token`. |
| POST | `/auth/refresh` | Rota el refresh token. |
| POST | `/auth/logout` | Revoca el refresh token del dispositivo. |
| GET | `/me` | Perfil, roles habilitados, contratista asociado, camiones propios. |
| PUT | `/me/dispositivo` | Registra o actualiza el token FCM. |
| GET | `/app/version` | Versión mínima soportada y estado del servicio. |

### 9.2 Catálogos

`GET/POST/PUT/DELETE` en `/catalogos/{contratistas|destinos|especies|largos|empresas-transporte}`. Lectura para todos los autenticados; escritura según 5.3. Los `DELETE` son lógicos.

### 9.3 Camiones

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/camiones` | Filtra por estado, alta, propietario. Respeta el rol. |
| POST | `/camiones` | Alta (transportista: queda `pendiente`; supervisor: `aprobada`). |
| PUT | `/camiones/{id}` | Edición. |
| DELETE | `/camiones/{id}` | Baja lógica (409 si está cargando). |
| POST | `/camiones/{id}/aprobar` · `/rechazar` | Solo supervisor. |
| POST | `/camiones/{id}/estado` | Cambios de estado permitidos (`fila`, `disponible`, `vacio`, `ruta`) con validaciones. |
| POST | `/camiones/{id}/incidencias` · `/incidencias/{iid}/resolver` | Falla o demora. |
| PUT | `/camiones/{id}/disponibilidad-manana` | `{valor: "si"|"no"}`; 409 pasada la hora de cierre. |
| GET | `/disponibilidad/resumen?fecha=` | Supervisor: disponibles, no disponibles, sin respuesta. |

### 9.4 Stock

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/stock?contratista_id=&tipo=&uso=` | Pilas vigentes. |
| PUT | `/contratistas/{id}/stock` | Reemplaza el relevamiento (lista de pilas). 409 pasado el cierre. |
| GET | `/stock/resumen` | Totales por largo, tipo y uso; último relevamiento por contratista. |

### 9.5 Programa

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/programa?jornada=hoy|manana` | Según rol: todo (supervisor) o solo lo propio. |
| PUT | `/programa/{jornada}` | Supervisor: reemplaza asignaciones y horas por contratista. |
| POST | `/programa/{jornada}/emitir` | Emite o reemite. |
| PUT | `/programa/{jornada}/prioridad/{contratista_id}` | `ninguna|pindo|ventas`; exige stock confirmado. |
| PUT | `/programa/manana/solicitud/{contratista_id}` | Elaborador: cantidad mínima y nota. DELETE para quitar. |
| PUT | `/programa/manana/inicio/{contratista_id}` | Elaborador: hora de inicio de carga. DELETE para quitar. |

### 9.6 Pedidos

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/pedidos` | Supervisor: todos con avance. |
| GET | `/pedidos/{contratista_id}` | Pedido con avance por línea y general (elaborador solo el propio). |
| PUT | `/pedidos/{contratista_id}` | Supervisor: líneas y nota. DELETE para quitar. |

Respuesta de avance: `{ pedido_total, enviado_total, cumplimiento_pct, faltante, lineas: [{tipo, largo, pedido, enviado, avance_pct, stock_pila}], fuera_de_pedido }`.

### 9.7 Cargas

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/cargas?jornada=&contratista_id=&estado=` | Listado. |
| POST | `/cargas` | Inicia carga de un camión programado (`programa_item_id`). |
| POST | `/cargas/{id}/finalizar` | `{circuito, rodal_id, destino_id, lineas[]}`. Valida y descuenta stock en una transacción. 409 con detalle si no hay stock. |
| POST | `/camiones/{id}/entrar-fila` | Registra `retorno_en` en la última carga abierta. |

### 9.8 Báscula

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/bascula/ingresos` | `{camion_id}` registra ingreso. |
| POST | `/bascula/ingresos/{id}/salida` | Registra salida y deja el camión `disponible`. |
| GET | `/bascula/hoy` | Descargando, ingresos y salidas, contadores. |
| GET | `/bascula/a-industria` | Camiones cargados con destino a industria. |
| GET | `/bascula/historico?desde=&hasta=` | Histograma por hora y promedios de descarga. |
| GET/POST/DELETE | `/bascula/turnos` · `/bascula/descansos` | Horarios. |

### 9.9 Análisis (supervisor)

`GET /analisis/ciclos?vista=punto|destino|cruce|transportistas&circuito=todos|industria|ventas&desde=&hasta=`
`GET /analisis/tiempos-carga?circuito=&desde=&hasta=`
`GET /analisis/demoras-inicio?desde=&hasta=`

### 9.10 Tarifario (jefe de área forestal)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/rodales` | Con sus tarifas vigentes. |
| POST | `/rodales` | `{codigo, contratista_id}`; 409 si el código existe. |
| DELETE | `/rodales/{id}` | Baja lógica; cierra sus tarifas. |
| PUT | `/rodales/{id}/tarifas/{destino_id}` | `{km_asfalto, km_tierra, tarifa_4x2, tarifa_6x4}`; crea nueva vigencia. |
| DELETE | `/rodales/{id}/tarifas/{destino_id}` | Cierra la vigencia. |
| POST | `/tarifas/importar?modo=previsualizar|confirmar` | Sube `.xlsx` o `.csv` con las columnas Empresa, Rodal, Destino, Km asfalto, Km tierra, 4x2, 6x4. Devuelve filas válidas, errores y rodales o destinos nuevos. |
| GET | `/tarifas?rodal=&destino=` | Lectura (transportista: solo la columna de su tracción cuando se pide `?para_camion=`). |

### 9.11 Remitos y facturación

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/remitos/foto` | Multipart con la imagen. Guarda, encola el OCR y devuelve `{remito_borrador_id}`. |
| GET | `/remitos/borradores/{id}` | Estado del OCR y datos leídos (polling o push). |
| POST | `/remitos` | Confirma el remito (datos corregidos por el usuario). Calcula importe. 409 por número repetido. |
| GET | `/remitos?camion_id=&desde=&hasta=` | Listado con importe y acumulado del mes. |
| GET | `/remitos/{id}` | Detalle con URL firmada de la foto. |
| DELETE | `/remitos/{id}` | Baja. |
| GET | `/camiones/{id}/facturacion?meses=6` | Resumen: mes actual, acumulado general, serie mensual, por rodal, avisos de control. |

### 9.12 Reportes

`GET /reportes/stock.pdf` (supervisor) y `GET /camiones/{id}/reportes/fletes.pdf?mes=` (transportista dueño). Ver sección 12.

### 9.13 Sincronización

`POST /sync/push` y `GET /sync/pull?cursor=` (sección 10).

---

## 10. Modo sin conexión y sincronización

El monte tiene mala señal: **la app debe poder usarse sin conexión** para lo esencial.

### 10.1 Qué funciona sin conexión

| Rol | Sin conexión se puede |
|---|---|
| Transportista | Ver su programa y datos cacheados, cambiar su estado, entrar/salir de fila, reportar incidencias, responder disponibilidad, **sacar foto de un remito** y dejarlo en cola para lectura. |
| Elaborador | Relevar stock, iniciar y finalizar cargas, marcar hora de inicio, pedir unidades. |
| Báscula | Registrar ingresos y salidas. |
| Supervisor / Jefe | Lectura de lo último sincronizado. Las escrituras de supervisión pueden exigir conexión (decisión pendiente, 19). |

### 10.2 Diseño

- **Room es la fuente de verdad de la UI.** La pantalla observa la base local; la red solo la alimenta.
- **Outbox**: tabla local de operaciones pendientes con `id` (UUID), `tipo`, `payload`, `creado_en`, `reintentos`, `estado`. Cada acción de escritura se aplica primero localmente (optimista) y se encola.
- **Subida**: `WorkManager` con restricción de red; reintentos con backoff exponencial; orden estricto por `creado_en` dentro de una misma entidad.
- **Bajada**: `GET /sync/pull?cursor=` devuelve cambios incrementales con tombstones de borrado y un nuevo cursor. Solo se descargan datos del ámbito del usuario.
- **Indicador**: chip "Sin conexión · N cambios sin enviar" y, al sincronizar, "Se enviaron N cambios".
- **Fotos de remitos**: se comprimen en el dispositivo (lado largo 1600 px, JPEG calidad 80 para la lectura; miniatura 400 px) y se suben en segundo plano.

### 10.3 Idempotencia

Todos los `id` nacen en el cliente. El servidor guarda la clave de cada operación procesada; si llega repetida, responde el resultado original sin duplicar.

### 10.4 Conflictos

| Entidad | Política |
|---|---|
| Relevamiento de stock | Gana el más reciente por `relevado_en` del lado del servidor; el anterior se archiva. |
| Estado del camión | Gana la transición válida más reciente; si es inválida se descarta y se avisa. |
| Finalizar carga | El servidor valida el stock. Si falta stock por otra carga que se sincronizó antes, responde `409` con el stock real; la app abre la carga para corregir volúmenes y reenviar. |
| Programa | Solo supervisor escribe; control optimista con `version`. En conflicto se muestra el estado del servidor. |
| Remito | Número repetido por camión → `409` y se ofrece abrir el existente. |

### 10.5 Reloj

Los eventos guardan la hora del dispositivo (`ocurrido_en`) y la hora de recepción del servidor. Se usa `ocurrido_en` para ciclos y tiempos siempre que la diferencia con el reloj del servidor sea razonable (< 10 minutos o corregida); si no, se marca como dato dudoso.

---

## 11. Lectura de remitos con foto (OCR)

En el prototipo la lectura la hace Claude con visión. En la app real:

1. La app saca la foto con CameraX (guía de encuadre, enfoque automático, flash opcional) y la comprime.
2. Sube la imagen a `POST /remitos/foto`. El backend la guarda en S3 y encola una tarea.
3. El worker envía la imagen a la API de visión (modelo configurable `VISION_MODEL`) con el prompt de abajo y los catálogos vigentes de rodales y destinos.
4. El backend valida la respuesta (JSON, tipos, rangos), normaliza el rodal contra el catálogo (mayúsculas, sin espacios ni guiones) y el destino por nombre aproximado, y guarda el borrador.
5. La app (por polling corto o push) abre el **formulario de revisión** con la foto y los datos prellenados. El usuario corrige y confirma. **Nunca se guarda un remito leído sin revisión humana.**
6. Si la lectura falla, el formulario se abre vacío con la foto adjunta para carga manual (`origen_dato = manual`).

Prompt de lectura (se reemplazan las listas entre llaves):

```text
La imagen es la foto de un remito de transporte de rollos de madera (Argentina).
Extraé los datos y respondé solo con un objeto JSON con esta forma:
{"numero": string|null, "fecha": "AAAA-MM-DD"|null, "rodal": string|null,
 "destino": string|null, "toneladas": number|null, "patente": string|null}
numero = número de remito. fecha = fecha del remito (en Argentina se escribe día/mes/año).
rodal = código del rodal o punto de carga (códigos conocidos: {lista_rodales}).
destino = lugar de descarga (destinos conocidos: {lista_destinos}).
toneladas = toneladas netas transportadas como número (si figuran bruto, tara y neto usá el neto;
si está en kg convertí a toneladas).
Si un dato no se lee con claridad usá null; no inventes valores.
```

Controles adicionales: límite de tamaño (10 MB), tipos permitidos (JPEG, PNG, WebP), límite de reintentos, registro del consumo de la API, y **degradación elegante** si la API no responde. Como alternativa o complemento puede evaluarse OCR en el dispositivo (ML Kit) para prellenar sin red.

---

## 12. Reportes PDF

Generados en el backend (ReportLab), A4 vertical, tipografía Helvetica, encabezado con el nombre de la app, fecha y hora de generación y pie con "Página N de M". Se entregan como `application/pdf` y la app los abre con el visor del sistema.

### 12.1 Reporte de stock (supervisor)

- Título, fecha y total pendiente en m³.
- **Stock general por largo** (m³): Largo, Fino, Grueso, Total, Stock Pindó SA, Stock ventas, con fila de totales.
- **Stock por contratista**: encabezado con total, último relevamiento (hora y nombre), Stock Pindó SA y Stock ventas; tabla por largo con Fino, Grueso, Total.

### 12.2 Reporte de rendimiento y facturación de fletes (transportista)

- Encabezado: transportista, patente, tracción, empresa y fecha de generación.
- **Resumen**: mes en curso (remitos, toneladas, facturación) y **acumulado general**.
- **Mes en curso por rodal**: Rodal, Contratista, Remitos, Toneladas, Facturación, con fila de totales.
- **Acumulado general por rodal**: mismas columnas con todos los remitos.
- **Facturación por mes**: Mes, Remitos, Toneladas, Facturación, **Acumulado**.
- Nota al pie con la cantidad de remitos sin tarifa, que no suman.

Los reportes se generan por demanda; los pesados van por tarea en segundo plano y la app recibe aviso al estar listos.

---

## 13. Notificaciones

| Evento | Destinatario | Mensaje |
|---|---|---|
| Programa emitido o reemitido | Transportistas y elaboradores asignados | "Tenés carga mañana a las HH:mm en {contratista}." |
| Alta de camión aprobada o rechazada | Transportista | Resultado del alta. |
| Alta de camión pendiente | Supervisor | "Hay N altas para aprobar." |
| Nuevo pedido o cambio de pedido | Elaborador del contratista | "El supervisor cargó/modificó tu pedido." |
| Faltan 60 min para el cierre de disponibilidad | Transportistas sin respuesta | "Marcá tu disponibilidad para mañana." |
| Faltan 60 min para el cierre de relevamiento | Elaboradores sin relevamiento del día | "Falta relevar el stock." |
| Remito leído listo para revisar | Quien lo subió | "Revisá los datos del remito." |
| Camión con incidencia | Supervisor | Falla mecánica o demora reportada. |
| Cambio de tarifario | Transportistas afectados (opcional) | "Se actualizaron tarifas de {rodal}." |

Canales de Android por tipo de aviso para que el usuario pueda silenciarlos por separado.

---

## 14. Seguridad, privacidad y auditoría

- **Transporte**: solo HTTPS (TLS 1.2+); HSTS; certificado válido. En la app, `network_security_config` sin tráfico en texto plano.
- **Autenticación**: contraseñas con Argon2; bloqueo progresivo por intentos fallidos; refresh tokens rotativos con detección de reuso; revocación por dispositivo.
- **Autorización**: dependencia de FastAPI por rol y por pertenencia en cada endpoint; pruebas automáticas que intentan acceder entre contratistas y entre transportistas.
- **Datos sensibles**: tokens en `EncryptedSharedPreferences`; sin datos personales en logs; fotos de remitos en un bucket privado con URL firmada de 5 minutos.
- **Protección de la API de visión**: la clave solo está en variables de entorno del servidor; límites de uso por usuario y por día.
- **Validación de entrada** estricta en todos los endpoints; límites de tamaño; protección contra inyección (consultas parametrizadas) y contra subida de archivos maliciosos (verificación de tipo real).
- **Auditoría**: cambios de tarifas, aprobación de camiones, emisión de programa, pedidos, finalización de cargas y borrado de remitos quedan en `auditoria` con antes y después.
- **Respaldo**: backup diario de PostgreSQL con retención de 30 días y prueba de restauración mensual; versionado del bucket de fotos.
- **Cumplimiento**: política de privacidad (Ley 25.326 de protección de datos personales, Argentina), consentimiento al alta, derecho de acceso y baja.
- **Modo de prueba**: el interruptor que da acceso a todos los roles solo existe en entornos `dev` y `staging`.

---

## 15. Requisitos no funcionales

- **Rendimiento**: p95 < 500 ms en lecturas y < 1 s en escrituras con 200 usuarios activos; el listado de remitos pagina.
- **Capacidad inicial**: 5 contratistas, 7 rodales (y creciendo), ~150 camiones, ~300 usuarios, ~400 cargas por día.
- **Disponibilidad**: 99,5 % mensual en horario operativo (5 a 23 h).
- **Móvil**: arranque en frío < 3 s en un equipo de gama media; consumo de datos moderado (sincronización incremental, imágenes comprimidas); funciona en Android 8.0 o superior.
- **Observabilidad**: métricas de latencia, errores 5xx, cola de tareas y consumo de la API de visión; alertas por correo o mensajería.
- **Mantenibilidad**: lint y tipado en CI, migraciones reversibles, documentación OpenAPI publicada, convención de commits y ramas (`main`, `develop`, `feature/*`).
- **Localización**: es-AR, huso `America/Argentina/Buenos_Aires` (sin horario de verano).
- **Accesibilidad**: contraste AA, fuentes escalables, no depender solo del color.

---

## 16. Estructura de repositorios y entornos

### 16.1 Repositorios

```
logistica-forestal-backend/    (Python)
logistica-forestal-android/    (Kotlin)
logistica-forestal-docs/       (opcional: este README, decisiones, runbooks)
```

### 16.2 Backend: variables de entorno

```
APP_ENV=dev|staging|prod
DATABASE_URL=postgresql+psycopg://user:pass@db:5432/logistica
REDIS_URL=redis://redis:6379/0
JWT_SECRET=...            JWT_ACCESS_MIN=15      JWT_REFRESH_DAYS=30
S3_ENDPOINT=...           S3_BUCKET=remitos       S3_ACCESS_KEY=...   S3_SECRET_KEY=...
FCM_PROJECT_ID=...        FCM_CREDENTIALS_JSON=...
ANTHROPIC_API_KEY=...     VISION_MODEL=...        VISION_DAILY_LIMIT_PER_USER=50
TZ=America/Argentina/Buenos_Aires
CIERRE_DISPONIBILIDAD=20:00
CIERRE_RELEVAMIENTO=21:00
TOLERANCIA_DEMORA_MIN=5
MODO_PRUEBA=false         # true solo en dev/staging
```

### 16.3 Entornos

- **dev**: Docker Compose local con datos semilla.
- **staging**: réplica de producción con datos de prueba y `MODO_PRUEBA` habilitable.
- **prod**: servidor de la empresa o nube; proxy inverso (Nginx o Traefik) con TLS.

### 16.4 CI/CD

- Backend: en cada PR `ruff`, `black --check`, `mypy`, `pytest` con base real en contenedor; build de imagen Docker; despliegue automático a staging al integrar en `develop` y manual a prod con aprobación.
- Android: `ktlintCheck`, `detekt`, pruebas unitarias, pruebas instrumentadas en emulador, build de `AAB` firmado por pipeline con el keystore en secretos.
- Migraciones: se ejecutan antes de levantar la nueva versión; se prueba el rollback.

### 16.5 Datos semilla

Para desarrollo: los catálogos de la sección 6.1, 5 contratistas de ejemplo, 7 rodales, tarifas de ejemplo (todas las combinaciones rodal × destino), 8 camiones, usuarios de prueba por rol y 14 remitos de ejemplo de un camión. **Los datos de producción se cargan desde catálogos y la planilla real del tarifario, no desde los datos semilla.**

---

## 17. Pruebas y criterios de aceptación

### 17.1 Estrategia

- **Unitarias** en `domain/`: avance de pedido, importe de remito, descuento de stock, demoras, ciclos, cierres por hora.
- **Integración** de API con PostgreSQL real: permisos por rol, idempotencia, transacciones de finalizar carga, importación del tarifario.
- **Contrato**: el esquema OpenAPI es la fuente; el cliente Kotlin se genera o valida contra él.
- **Android**: pruebas de ViewModel con Turbine, Room en memoria, pruebas de UI Compose de los flujos críticos y prueba de sincronización con servidor simulado.
- **Carga**: script con 200 usuarios simultáneos en horario pico de relevamiento.
- **Pruebas de seguridad**: intentos de escalada entre roles y entre contratistas.

### 17.2 Criterios de aceptación clave (Dado / Cuando / Entonces)

1. **Cierre de relevamiento**
   - Dado que son las 21:01, cuando un elaborador intenta guardar un relevamiento, entonces el servidor responde 409 y la app muestra "Relevamiento cerrado".
2. **Descuento de stock por circuito**
   - Dado stock `pindo` 10 m³ y `ventas` 10 m³ del mismo tipo y largo, cuando se finaliza una carga a industria de 12 m³, entonces se rechaza por stock insuficiente (las pilas de ventas no se consumen).
3. **Aviso de descarga solo para ventas**
   - Dado un camión cuya última carga fue a industria, cuando el transportista abre "Mi viaje", entonces no ve los botones de aviso de descarga ni de disponibilidad; al registrar la salida en báscula el camión queda disponible.
4. **Avance de pedido**
   - Dado un pedido de 60 m³ grueso 12 y 30 m³ fino 10, cuando se finalizan cargas por 70 m³ grueso 12 y 0 de fino 10, entonces el cumplimiento general es 66,7 % (60 de 90) y el exceso de 10 m³ no compensa la otra línea.
5. **Tarifa por tracción**
   - Dado un remito con rodal `PIEDIESEL`, destino `Cliente Norte` y un camión 4x2, cuando se confirma, entonces el importe es la tarifa 4x2 vigente; con un camión 6x4 es la tarifa 6x4.
6. **Remito sin tarifa**
   - Dado un remito sin destino, cuando se guarda, entonces queda "Sin tarifa", no suma a la facturación y la app lo avisa.
7. **Permisos del tarifario**
   - Dado un usuario supervisor, cuando llama a cualquier endpoint de `/rodales` o `/tarifas` para escribir o leer, entonces recibe 403.
8. **Jefe en solo lectura**
   - Dado un jefe viendo el panel de un camión, cuando intenta registrar una incidencia, entonces recibe 403 y la app no muestra el botón.
9. **Offline**
   - Dado un elaborador sin conexión, cuando finaliza una carga, entonces la acción queda en cola, la UI se actualiza y al recuperar señal se sincroniza; si el servidor detecta stock insuficiente, la app abre la carga para corregir.
10. **Remito duplicado**
    - Dado un número ya cargado para el camión, cuando se intenta guardar otro igual, entonces se informa y se ofrece abrir el existente.
11. **Disponibilidad**
    - Dado que son las 20:01, cuando el transportista cambia su disponibilidad para mañana, entonces se rechaza y se muestra que la respuesta cerró.
12. **Demora de inicio**
    - Dado un inicio confirmado a las 07:30 y un primer inicio real a las 07:50, entonces la demora es 20 min; con inicio real a las 07:34 se considera a horario.

---

## 18. Plan de entrega por fases

| Fase | Contenido | Resultado demostrable |
|---|---|---|
| **0. Cimientos** | Repos, CI, Docker Compose, esquema base, autenticación y roles, catálogos, perfil de usuario, pantalla de selección de rol, `GET /app/version`. | Login y navegación por rol con datos semilla. |
| **1. Núcleo operativo** | Camiones (alta, aprobación, baja, estados, incidencias), relevamiento de stock, programa de carga con emisión, disponibilidad de mañana, prioridad, solicitudes e inicio de carga. | El supervisor arma y emite el programa y el transportista lo ve. |
| **2. Despachos y báscula** | Cargas (iniciar, finalizar con rodal y destino), descuento de stock, ciclo y fila, báscula (ingreso, salida, horarios, histórico), avisos de ventas. | Un día completo de operación punta a punta. |
| **3. Offline y sincronización** | Room, outbox, WorkManager, pull incremental, conflictos, indicadores de conexión, FCM. | La operación sigue sin señal y se sincroniza. |
| **4. Pedidos y análisis** | Pedidos de rollos con avance, tablero de supervisor, análisis de ciclos, tiempos de carga y demoras de inicio, reporte PDF de stock. | Supervisor con tableros y reportes. |
| **5. Tarifario y facturación** | Rodales y tarifas, importación desde planilla, remitos con foto y lectura por IA, facturación mensual, reporte PDF de fletes, rol del jefe con paneles de solo lectura. | Transportista factura por remitos; el jefe administra el tarifario. |
| **6. Endurecimiento** | Pruebas de carga y seguridad, auditoría completa, backups, monitoreo, manual de usuario, publicación en Play. | Producción estable. |

Cada fase termina con demo, pruebas en verde y notas de versión.

---

## 19. Decisiones y datos pendientes

1. **Hosting del backend**: servidor propio de la empresa o nube administrada (por ejemplo base de datos gestionada). Define backups, red y costos.
2. **Autenticación real**: usuario y contraseña, teléfono con código por SMS/WhatsApp, o integración con un directorio de la empresa.
3. **Catálogos reales**: lista de contratistas, empresas de transporte, rodales, destinos (con circuito industria/ventas) y la planilla completa del tarifario con vigencias.
4. **Tarifa por viaje o por tonelada**: el prototipo asume un valor fijo por flete (viaje) según rodal, destino y tracción. Si el pago es por tonelada o por m³, el cálculo del importe cambia (`importe = tarifa × toneladas`).
5. **Tolerancias**: confirmar cierre de disponibilidad (20:00), cierre de relevamiento (21:00) y tolerancia de demora (5 min).
6. **Escrituras del supervisor sin conexión**: ¿pueden hacerse offline o requieren conexión?
7. **Pesaje**: quedó fuera del alcance; confirmar si se retomará en una versión posterior (bruto, tara, neto, ticket).
8. **Facturación**: hoy el sistema calcula importes de control. Definir si se integrará con el circuito de pagos o liquidación.
9. **Supervisión de remitos**: el supervisor no ve los remitos de los transportistas. Evaluar una pantalla de control de remitos contra despachos.
10. **Logo e identidad visual** de Pindó SA para el ícono de la app y la pantalla de inicio.
11. **Política de retención de fotos de remitos** (por ejemplo 5 años por obligación fiscal) y costo de almacenamiento.
12. **Rol `admin`**: quién administra usuarios y catálogos en producción.
13. **Variación del período en curso**: en el prototipo la variación mensual del mes en curso no se muestra por estar incompleto el mes; confirmar si se desea comparar contra el mismo tramo del mes anterior.
14. **Análisis por rodal**: hoy "punto de carga" en los análisis agrupa por contratista; evaluar agrupar por rodal.

---

## 20. Glosario

- **Rodal**: unidad de bosque identificada por un código; en esta app es el **punto de carga** y la base del tarifario.
- **Contratista / elaborador**: empresa que procesa (corta, desrama, apila) los rollos en el rodal.
- **Pila**: acopio de rollos del mismo tipo y largo.
- **Rollo fino / grueso**: categorías de rollo por diámetro.
- **Largo (pies)**: largo del rollo en pies (8, 10, 12, 14, 16, 18, 20).
- **Stock Pindó SA / stock de ventas**: rollos destinados a industria propia o reservados para venta.
- **Circuito**: destino comercial de una carga: `industria` (propia) o `ventas`.
- **Frente**: lugar de carga de un contratista, con su cola de camiones.
- **Programa**: asignación de camiones a frentes con hora para una jornada (hoy o mañana).
- **Jornada**: día operativo en hora de Argentina.
- **Ciclo**: tiempo entre la salida cargado del punto de carga y el retorno a la fila del mismo.
- **Báscula**: control de ingreso y salida de camiones en la planta de descarga.
- **Remito**: comprobante de transporte del flete; en la app se fotografía y se lee.
- **Tarifario**: lista de tarifas por rodal, destino y tracción; lo administra el Jefe de Área Forestal.
- **4x2 / 6x4**: configuración de tracción del camión; define qué columna de tarifa se aplica.
- **Outbox**: cola local de operaciones del móvil pendientes de enviar al servidor.
- **Idempotente**: repetir la misma operación no duplica su efecto.
