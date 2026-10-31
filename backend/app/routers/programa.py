"""Programa de carga: armado y emisión (supervisor), prioridad por frente, solicitud de unidades e inicio de carga (elaborador)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth, consultas as q, db
from ..util import ApiError, ahora, auditar, hora_valida, hoy, jornada_de, manana, nuevo_id, uuid_ok

router = APIRouter(tags=["programa"])


class Item(BaseModel):
    id: str | None = None
    camion_id: str
    contratista_id: str
    hora: str


class Asignaciones(BaseModel):
    items: list[Item] = Field(min_length=1, max_length=300)


class Prioridad(BaseModel):
    prioridad: str  # ninguna | pindo | ventas


class Solicitud(BaseModel):
    cantidad_minima: int = Field(ge=1, le=99)
    nota: str | None = Field(default=None, max_length=200)


class Inicio(BaseModel):
    hora: str


def _jornada_editable(j):
    d = jornada_de(j)
    if d not in (hoy(), manana()):
        raise ApiError(422, "jornada", "Sólo se programa hoy o mañana")
    return d


@router.post("/programa/{jornada}/items", status_code=201)
def programar(jornada: str, d: Asignaciones, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    j = _jornada_editable(jornada)
    inc = q.incidencias_abiertas(cn)
    disp = q.disponibilidad(cn, j) if j == manana() else {}
    creados = []
    for it in d.items:
        if not hora_valida(it.hora):
            raise ApiError(422, "hora", "Hora inválida")
        gid = uuid_ok(it.id) if it.id else nuevo_id()
        if db.one(cn, "SELECT id FROM dbo.ZTLOGI_PROGRAMA WHERE id = ?", gid):
            creados.append(gid)
            continue
        c = db.one(cn, "SELECT id, patente, estado FROM dbo.ZTLOGI_CAMIONES WHERE id = ? AND baja = 0 AND alta_estado = 'aprobada'", uuid_ok(it.camion_id))
        if not c:
            raise ApiError(422, "camion", "Camión inexistente o no aprobado")
        if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE id = ? AND activo = 1", uuid_ok(it.contratista_id)):
            raise ApiError(422, "contratista", "Contratista inexistente")
        if j == hoy() and inc.get(c["id"], {}).get("tipo") == "mecanico":
            raise ApiError(409, "mecanico", f"{c['patente']} tiene un problema mecánico. Cerrá la novedad antes de programarlo.")
        if disp.get(c["id"], {}).get("valor") == "no":
            raise ApiError(409, "no_disponible", f"{c['patente']} avisó que no está disponible mañana")
        if db.one(cn, "SELECT id FROM dbo.ZTLOGI_PROGRAMA WHERE jornada = ? AND camion_id = ? AND estado IN ('programado','cargando')", j, c["id"]):
            raise ApiError(409, "ya_programado", f"{c['patente']} ya tiene una carga programada ese día")
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PROGRAMA (id, jornada, camion_id, contratista_id, hora, estado, creado_por, created_at, updated_at) VALUES (?,?,?,?,?,'programado',?,?,?)",
               gid, j, c["id"], it.contratista_id, it.hora, user["id"], ahora(), ahora())
        creados.append(gid)
    auditar(cn, "programa", j.isoformat(), "programar", None, [i.model_dump() for i in d.items], user, user["_ip"])
    return {"ids": creados}


@router.delete("/programa/items/{gid}")
def quitar(gid: str, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    g = db.one(cn, "SELECT * FROM dbo.ZTLOGI_PROGRAMA WHERE id = ?", uuid_ok(gid))
    if g and g["estado"] == "programado":
        db.run(cn, "UPDATE dbo.ZTLOGI_PROGRAMA SET estado = 'quitado', updated_at = ? WHERE id = ?", ahora(), g["id"])
        auditar(cn, "programa", g["id"], "quitar", g, None, user, user["_ip"])
    return {"ok": True}


@router.post("/programa/{jornada}/emitir")
def emitir(jornada: str, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    j = _jornada_editable(jornada)
    n = db.scalar(cn, "SELECT COUNT(*) FROM dbo.ZTLOGI_PROGRAMA WHERE jornada = ? AND estado IN ('programado','cargando')", j)
    if not n:
        raise ApiError(409, "vacio", "El programa está vacío. Programá al menos un camión.")
    db.run(cn, "INSERT INTO dbo.ZTLOGI_PROGRAMA_EMISIONES (jornada, emitido_por, emitido_en) VALUES (?,?,?)", j, user["id"], ahora())
    auditar(cn, "programa", j.isoformat(), "emision", None, {"camiones": n}, user, user["_ip"])
    return {"jornada": j.isoformat(), "emitido_en": ahora().strftime("%Y-%m-%dT%H:%M:%S"), "camiones": n}


@router.put("/programa/{jornada}/prioridad/{contratista_id}")
def prioridad(jornada: str, contratista_id: str, d: Prioridad, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    j = _jornada_editable(jornada)
    cid = uuid_ok(contratista_id)
    if d.prioridad not in ("ninguna", "pindo", "ventas"):
        raise ApiError(422, "prioridad", "Prioridad inválida")
    if j == manana() and d.prioridad != "ninguna" and not db.one(cn, "SELECT TOP 1 id FROM dbo.ZTLOGI_PILAS WHERE contratista_id = ? AND eliminada = 0 AND volumen_m3 > 0", cid):
        raise ApiError(409, "sin_stock", "El contratista todavía no confirmó su stock")
    db.run(cn, "DELETE FROM dbo.ZTLOGI_PRIORIDAD_FRENTE WHERE jornada = ? AND contratista_id = ?", j, cid)
    if d.prioridad != "ninguna":
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PRIORIDAD_FRENTE (jornada, contratista_id, prioridad, usuario_id, en) VALUES (?,?,?,?,?)", j, cid, d.prioridad, user["id"], ahora())
    return {"jornada": j.isoformat(), "contratista_id": cid, "prioridad": d.prioridad}


@router.put("/programa/manana/solicitud")
def solicitar(d: Solicitud, user=Depends(auth.requiere("elaborador"))):
    cn = user["_cn"]
    cid = q.contratista_propio(cn, user)
    m = manana()
    db.run(cn, "DELETE FROM dbo.ZTLOGI_SOLICITUDES_UNIDADES WHERE jornada = ? AND contratista_id = ?", m, cid)
    db.run(cn, "INSERT INTO dbo.ZTLOGI_SOLICITUDES_UNIDADES (jornada, contratista_id, cantidad_minima, nota, solicitada_por, usuario_id, solicitada_en) VALUES (?,?,?,?,?,?,?)",
           m, cid, d.cantidad_minima, (d.nota or "").strip() or None, user["nombre"], user["id"], ahora())
    return {"jornada": m.isoformat(), "cantidad_minima": d.cantidad_minima, "nota": d.nota, "solicitada_por": user["nombre"], "solicitada_en": ahora().strftime("%Y-%m-%dT%H:%M:%S")}


@router.delete("/programa/manana/solicitud")
def quitar_solicitud(user=Depends(auth.requiere("elaborador"))):
    cn = user["_cn"]
    db.run(cn, "DELETE FROM dbo.ZTLOGI_SOLICITUDES_UNIDADES WHERE jornada = ? AND contratista_id = ?", manana(), q.contratista_propio(cn, user))
    return {"ok": True}


@router.put("/programa/{jornada}/inicio")
def inicio(jornada: str, d: Inicio, user=Depends(auth.requiere("elaborador"))):
    cn = user["_cn"]
    j = _jornada_editable(jornada)
    cid = q.contratista_propio(cn, user)
    if not hora_valida(d.hora):
        raise ApiError(422, "hora", "Ingresá una hora válida")
    db.run(cn, "DELETE FROM dbo.ZTLOGI_INICIO_CARGA WHERE jornada = ? AND contratista_id = ?", j, cid)
    db.run(cn, "INSERT INTO dbo.ZTLOGI_INICIO_CARGA (jornada, contratista_id, hora, marcado_por, usuario_id, marcado_en) VALUES (?,?,?,?,?,?)", j, cid, d.hora, user["nombre"], user["id"], ahora())
    return {"jornada": j.isoformat(), "hora": d.hora, "marcado_por": user["nombre"], "marcado_en": ahora().strftime("%Y-%m-%dT%H:%M:%S")}


@router.delete("/programa/{jornada}/inicio")
def quitar_inicio(jornada: str, user=Depends(auth.requiere("elaborador"))):
    cn = user["_cn"]
    db.run(cn, "DELETE FROM dbo.ZTLOGI_INICIO_CARGA WHERE jornada = ? AND contratista_id = ?", _jornada_editable(jornada), q.contratista_propio(cn, user))
    return {"ok": True}
