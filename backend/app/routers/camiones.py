"""Camiones: alta (transportista pendiente / supervisor aprobada), edición, baja, aprobación, estados, fila, incidencias, disponibilidad."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth, config, consultas as q, db, reglas
from ..util import ApiError, ahora, auditar, cierre_pasado, hoy, manana, nuevo_id, parse_ocurrido, uuid_ok

router = APIRouter(tags=["camiones"])
MOTIVOS = {
    "mecanico": ["Neumático", "Frenos", "Motor", "Sistema eléctrico", "Acoplado o pluma", "Otro"],
    "demora": ["Espera en balanza", "Espera para descargar", "Ruta o camino cortado", "Clima", "Documentación", "Otro"],
}


class Camion(BaseModel):
    id: str | None = None
    patente: str = Field(min_length=5, max_length=12)
    chofer: str = Field(min_length=3, max_length=120)
    telefono: str | None = Field(default=None, max_length=30)
    empresa: str = Field(min_length=2, max_length=120)
    capacidad_tn: float = Field(gt=0, le=99.9)
    traccion: str


class Estado(BaseModel):
    estado: str
    ocurrido_en: str | None = None


class EventoHora(BaseModel):
    ocurrido_en: str | None = None


class Incidencia(BaseModel):
    id: str | None = None
    tipo: str
    motivo: str = Field(max_length=60)
    detalle: str | None = Field(default=None, max_length=300)
    minutos: int | None = Field(default=None, ge=1, le=1440)
    ocurrido_en: str | None = None


class Disponibilidad(BaseModel):
    valor: str
    ocurrido_en: str | None = None


def _camion(cn, cid):
    c = db.one(cn, f"SELECT {q.CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.id = ?", uuid_ok(cid))
    if not c or c["baja"]:
        raise ApiError(404, "camion_inexistente", "Camión inexistente")
    return c


def _validar(d: Camion):
    if d.traccion not in ("4x2", "6x4"):
        raise ApiError(422, "traccion", "La tracción debe ser 4x2 o 6x4")
    pat = " ".join(d.patente.upper().split())
    if len(reglas.patente_norm(pat)) < 5:
        raise ApiError(422, "patente", "Ingresá una patente válida")
    return pat


@router.post("/camiones", status_code=201)
def alta(d: Camion, user=Depends(auth.requiere("transportista", "supervisor"))):
    cn = user["_cn"]
    pat = _validar(d)
    cid = uuid_ok(d.id) if d.id else nuevo_id()
    ex = db.one(cn, "SELECT id FROM dbo.ZTLOGI_CAMIONES WHERE id = ?", cid)
    if ex:
        return _camion(cn, cid)  # idempotente
    if db.one(cn, "SELECT id FROM dbo.ZTLOGI_CAMIONES WHERE patente_norm = ? AND baja = 0 AND alta_estado <> 'rechazada'", reglas.patente_norm(pat)):
        raise ApiError(409, "patente_duplicada", f"Ya existe un camión con la patente {pat}")
    sup = auth.tiene_rol(user, "supervisor")
    db.run(
        cn,
        "INSERT INTO dbo.ZTLOGI_CAMIONES (id, patente, patente_norm, chofer, telefono, empresa, capacidad_tn, traccion, estado, alta_estado, alta_en, alta_por, propietario_usuario_id, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,'disponible',?,?,?,?,?,?)",
        cid, pat, reglas.patente_norm(pat), " ".join(d.chofer.split()), (d.telefono or "").strip() or None, d.empresa.strip(), round(d.capacidad_tn, 1), d.traccion,
        "aprobada" if sup else "pendiente", ahora(), user["nombre"], user["id"], ahora(), ahora(),
    )
    auditar(cn, "camion", cid, "alta", None, d.model_dump(), user, user["_ip"])
    return _camion(cn, cid)


@router.put("/camiones/{cid}")
def editar(cid: str, d: Camion, user=Depends(auth.requiere("transportista", "supervisor"))):
    cn = user["_cn"]
    c = _camion(cn, cid)
    if not auth.tiene_rol(user, "supervisor"):
        q.camion_propio(cn, user, cid)
    pat = _validar(d)
    dup = db.one(cn, "SELECT id FROM dbo.ZTLOGI_CAMIONES WHERE patente_norm = ? AND baja = 0 AND alta_estado <> 'rechazada' AND id <> ?", reglas.patente_norm(pat), c["id"])
    if dup:
        raise ApiError(409, "patente_duplicada", f"Ya existe un camión con la patente {pat}")
    db.run(
        cn,
        "UPDATE dbo.ZTLOGI_CAMIONES SET patente = ?, patente_norm = ?, chofer = ?, telefono = ?, empresa = ?, capacidad_tn = ?, traccion = ?, version = version + 1, updated_at = ? WHERE id = ?",
        pat, reglas.patente_norm(pat), " ".join(d.chofer.split()), (d.telefono or "").strip() or None, d.empresa.strip(), round(d.capacidad_tn, 1), d.traccion, ahora(), c["id"],
    )
    auditar(cn, "camion", c["id"], "edicion", c, d.model_dump(), user, user["_ip"])
    return _camion(cn, cid)


@router.delete("/camiones/{cid}")
def baja(cid: str, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    c = _camion(cn, cid)
    if c["estado"] == "cargando":
        raise ApiError(409, "cargando", "Este camión está cargando ahora. Finalizá la carga antes de eliminarlo.")
    db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET baja = 1, fila_desde = NULL, fila_contratista_id = NULL, updated_at = ? WHERE id = ?", ahora(), c["id"])
    db.run(cn, "UPDATE dbo.ZTLOGI_PROGRAMA SET estado = 'quitado', updated_at = ? WHERE camion_id = ? AND estado = 'programado'", ahora(), c["id"])
    db.run(cn, "UPDATE dbo.ZTLOGI_INCIDENCIAS SET resuelta_en = ? WHERE camion_id = ? AND resuelta_en IS NULL", ahora(), c["id"])
    auditar(cn, "camion", c["id"], "baja", c, None, user, user["_ip"])
    return {"ok": True}


@router.post("/camiones/{cid}/aprobar")
def aprobar(cid: str, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    c = _camion(cn, cid)
    if c["alta_estado"] == "pendiente":
        db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET alta_estado = 'aprobada', updated_at = ? WHERE id = ?", ahora(), c["id"])
        auditar(cn, "camion", c["id"], "aprobacion", {"alta_estado": "pendiente"}, {"alta_estado": "aprobada"}, user, user["_ip"])
    return _camion(cn, cid)


@router.post("/camiones/{cid}/rechazar")
def rechazar(cid: str, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    c = _camion(cn, cid)
    if c["alta_estado"] == "pendiente":
        db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET alta_estado = 'rechazada', updated_at = ? WHERE id = ?", ahora(), c["id"])
        auditar(cn, "camion", c["id"], "rechazo", {"alta_estado": "pendiente"}, {"alta_estado": "rechazada"}, user, user["_ip"])
    return _camion(cn, cid)


@router.post("/camiones/{cid}/reintentar-alta")
def reintentar(cid: str, user=Depends(auth.requiere("transportista"))):
    """Un alta rechazada se descarta (baja lógica) para poder cargar otra."""
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid)
    if c["alta_estado"] != "rechazada":
        raise ApiError(409, "no_rechazada", "El alta no está rechazada")
    db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET baja = 1, updated_at = ? WHERE id = ?", ahora(), c["id"])
    return {"ok": True}


def _ultima_carga(cn, camion_id):
    return db.one(cn, "SELECT TOP 1 id, circuito, retorno_en FROM dbo.ZTLOGI_CARGAS WHERE camion_id = ? AND estado = 'finalizada' ORDER BY fin_en DESC", camion_id)


@router.post("/camiones/{cid}/estado")
def cambiar_estado(cid: str, d: Estado, user=Depends(auth.requiere("transportista"))):
    """Aviso de descarga (ventas): ruta -> vacio -> disponible. Sólo si la última carga fue a ventas."""
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid)
    if c["alta_estado"] != "aprobada":
        raise ApiError(403, "alta_pendiente", "El alta del camión no está aprobada")
    u = _ultima_carga(cn, c["id"])
    if u and u["circuito"] == "industria":
        raise ApiError(409, "descarga_industria", "Tu carga va a industria propia: la descarga y la disponibilidad las registra la báscula")
    trans = {("ruta", "vacio"), ("vacio", "disponible"), ("ruta", "disponible")}
    if (c["estado"], d.estado) not in trans:
        raise ApiError(409, "transicion_invalida", f"No se puede pasar de {c['estado']} a {d.estado}")
    db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = ?, updated_at = ? WHERE id = ?", d.estado, ahora(), c["id"])
    auditar(cn, "camion", c["id"], "estado", {"estado": c["estado"]}, {"estado": d.estado}, user, user["_ip"])
    return _camion(cn, cid)


@router.post("/camiones/{cid}/entrar-fila")
def entrar_fila(cid: str, d: EventoHora | None = None, user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid)
    if c["alta_estado"] != "aprobada":
        raise ApiError(403, "alta_pendiente", "El alta del camión no está aprobada")
    if c["id"] in q.incidencias_abiertas(cn) and q.incidencias_abiertas(cn)[c["id"]]["tipo"] == "mecanico":
        raise ApiError(409, "mecanico", "Tenés un problema mecánico abierto")
    g = db.one(cn, "SELECT TOP 1 id, contratista_id FROM dbo.ZTLOGI_PROGRAMA WHERE jornada = ? AND camion_id = ? AND estado = 'programado' ORDER BY hora", hoy(), c["id"])
    if not g:
        raise ApiError(409, "sin_programa", "No tenés carga programada hoy")
    if c["estado"] == "fila":
        return _camion(cn, cid)
    if c["estado"] not in ("disponible", "vacio"):
        raise ApiError(409, "estado", f"No podés entrar en fila estando {c['estado']}")
    en = parse_ocurrido(d.ocurrido_en if d else None)
    u = _ultima_carga(cn, c["id"])
    if u and not u["retorno_en"]:
        db.run(cn, "UPDATE dbo.ZTLOGI_CARGAS SET retorno_en = ? WHERE id = ?", en, u["id"])
    db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = 'fila', fila_desde = ?, fila_contratista_id = ?, updated_at = ? WHERE id = ?", en, g["contratista_id"], ahora(), c["id"])
    return _camion(cn, cid)


@router.post("/camiones/{cid}/salir-fila")
def salir_fila(cid: str, d: EventoHora | None = None, user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid)
    if c["estado"] == "fila":
        db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = 'disponible', fila_desde = NULL, fila_contratista_id = NULL, updated_at = ? WHERE id = ?", ahora(), c["id"])
    return _camion(cn, cid)


@router.post("/camiones/{cid}/incidencias", status_code=201)
def incidencia(cid: str, d: Incidencia, user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid)
    if d.tipo not in MOTIVOS or d.motivo not in MOTIVOS[d.tipo]:
        raise ApiError(422, "motivo", "Motivo inválido")
    iid = uuid_ok(d.id) if d.id else nuevo_id()
    if db.one(cn, "SELECT id FROM dbo.ZTLOGI_INCIDENCIAS WHERE id = ?", iid):
        return {"id": iid}
    en = parse_ocurrido(d.ocurrido_en)
    db.run(cn, "UPDATE dbo.ZTLOGI_INCIDENCIAS SET resuelta_en = ? WHERE camion_id = ? AND resuelta_en IS NULL", en, c["id"])
    db.run(cn, "INSERT INTO dbo.ZTLOGI_INCIDENCIAS (id, camion_id, tipo, motivo, detalle, minutos, desde, creada_por) VALUES (?,?,?,?,?,?,?,?)",
           iid, c["id"], d.tipo, d.motivo, (d.detalle or "").strip() or None, d.minutos if d.tipo == "demora" else None, en, user["id"])
    if d.tipo == "mecanico" and c["estado"] == "fila":
        db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = 'disponible', fila_desde = NULL, fila_contratista_id = NULL, updated_at = ? WHERE id = ?", ahora(), c["id"])
    auditar(cn, "incidencia", iid, "alta", None, d.model_dump(), user, user["_ip"])
    return {"id": iid}


@router.post("/camiones/{cid}/incidencias/resolver")
def resolver(cid: str, d: EventoHora | None = None, user=Depends(auth.requiere("transportista", "supervisor"))):
    cn = user["_cn"]
    c = _camion(cn, cid)
    if not auth.tiene_rol(user, "supervisor"):
        q.camion_propio(cn, user, cid)
    en = parse_ocurrido(d.ocurrido_en if d else None)
    db.run(cn, "UPDATE dbo.ZTLOGI_INCIDENCIAS SET resuelta_en = ? WHERE camion_id = ? AND resuelta_en IS NULL", en, c["id"])
    return _camion(cn, cid)


@router.put("/camiones/{cid}/disponibilidad-manana")
def disponibilidad_manana(cid: str, d: Disponibilidad, user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid)
    if d.valor not in ("si", "no"):
        raise ApiError(422, "valor", "Valor inválido")
    en = parse_ocurrido(d.ocurrido_en)
    if cierre_pasado(config.CIERRE_DISPONIBILIDAD, en):
        raise ApiError(409, "cierre", f"La respuesta cerró a las {config.CIERRE_DISPONIBILIDAD} hs")
    m = manana()
    if db.one(cn, "SELECT camion_id FROM dbo.ZTLOGI_DISPONIBILIDAD WHERE camion_id = ? AND jornada = ?", c["id"], m):
        db.run(cn, "UPDATE dbo.ZTLOGI_DISPONIBILIDAD SET valor = ?, respondida_en = ? WHERE camion_id = ? AND jornada = ?", d.valor, en, c["id"], m)
    else:
        db.run(cn, "INSERT INTO dbo.ZTLOGI_DISPONIBILIDAD (camion_id, jornada, valor, respondida_en) VALUES (?,?,?,?)", c["id"], m, d.valor, en)
    return {"camion_id": c["id"], "jornada": m.isoformat(), "valor": d.valor}


@router.get("/disponibilidad/resumen")
def resumen_disponibilidad(user=Depends(auth.requiere("supervisor", "jefe"))):
    cn = user["_cn"]
    m = manana()
    cam = db.rows(cn, "SELECT c.id, c.patente, c.chofer, d.valor, d.respondida_en FROM dbo.ZTLOGI_CAMIONES c LEFT JOIN dbo.ZTLOGI_DISPONIBILIDAD d ON d.camion_id = c.id AND d.jornada = ? "
                  "WHERE c.baja = 0 AND c.alta_estado = 'aprobada' ORDER BY c.patente", m)
    return {"jornada": m.isoformat(), "disponibles": [c for c in cam if c["valor"] == "si"], "no_disponibles": [c for c in cam if c["valor"] == "no"], "sin_respuesta": [c for c in cam if not c["valor"]]}
