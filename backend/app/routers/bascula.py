"""Báscula: ingreso y salida de camiones, horarios y descansos, histórico."""
import datetime as dt

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth, db
from ..util import ApiError, ahora, auditar, hhmm, hora_valida, hoy, mins, nuevo_id, parse_ocurrido, uuid_ok

router = APIRouter(tags=["bascula"])


class Ingreso(BaseModel):
    id: str | None = None
    camion_id: str
    ocurrido_en: str | None = None


class Salida(BaseModel):
    ocurrido_en: str | None = None


class Franja(BaseModel):
    id: str | None = None
    desde: str
    hasta: str
    motivo: str | None = Field(default=None, max_length=120)


def estado_bascula(cn):
    now = hhmm()
    desc = db.rows(cn, "SELECT desde, hasta, motivo FROM dbo.ZTLOGI_BASCULA_DESCANSOS ORDER BY desde")
    turnos = db.rows(cn, "SELECT desde, hasta FROM dbo.ZTLOGI_BASCULA_TURNOS ORDER BY desde")
    d = next((x for x in desc if x["desde"] <= now < x["hasta"]), None)
    if d:
        return {"k": "desc", "t": f"En descanso hasta las {d['hasta']}" + (f" · {d['motivo']}" if d["motivo"] else "")}
    t = next((x for x in turnos if x["desde"] <= now < x["hasta"]), None)
    if t:
        pd = next((x for x in desc if now < x["desde"] < t["hasta"]), None)
        return {"k": "ok", "t": f"Atendiendo hasta las {t['hasta']}" + (f" · próximo descanso {pd['desde']}" if pd else "")}
    nx = next((x for x in turnos if x["desde"] > now), None)
    return {"k": "cerr", "t": f"Cerrada · abre a las {nx['desde']}" if nx else "Cerrada por hoy"}


def historico_bascula(cn, dias=30):
    desde = hoy() - dt.timedelta(days=dias)
    rs = db.rows(cn, "SELECT jornada, ingreso_en, salida_en FROM dbo.ZTLOGI_BASCULA_MOV WHERE jornada >= ? ORDER BY jornada, ingreso_en", desde)
    por_dia, por_hora = {}, {h: 0 for h in range(5, 21)}
    durs = []
    for r in rs:
        ing = dt.datetime.fromisoformat(r["ingreso_en"])
        d = por_dia.setdefault(r["jornada"], {"jornada": r["jornada"], "n": 0, "horas": {}, "durs": []})
        d["n"] += 1
        d["horas"][ing.hour] = d["horas"].get(ing.hour, 0) + 1
        por_hora[ing.hour] = por_hora.get(ing.hour, 0) + 1
        if r["salida_en"]:
            m = (dt.datetime.fromisoformat(r["salida_en"]) - ing).total_seconds() / 60
            if m >= 0:
                durs.append(m)
                d["durs"].append(m)
    nd = len(por_dia) or 1
    dias_out = []
    for d in sorted(por_dia.values(), key=lambda x: x["jornada"], reverse=True):
        pico = max(d["horas"].items(), key=lambda kv: kv[1]) if d["horas"] else (None, 0)
        dias_out.append({"jornada": d["jornada"], "n": d["n"], "pico_h": pico[0], "pico_n": pico[1], "prom_min": round(sum(d["durs"]) / len(d["durs"])) if d["durs"] else None})
    pico_h = max(por_hora.items(), key=lambda kv: kv[1])[0] if rs else None
    return {"dias_n": len(por_dia), "total": len(rs), "prom_min": round(sum(durs) / len(durs)) if durs else None, "camiones_por_dia": round(len(rs) / nd, 1),
            "pico_h": pico_h, "por_hora": {str(h): round(n / nd, 1) for h, n in por_hora.items()}, "dias": dias_out}


@router.post("/bascula/ingresos", status_code=201)
def ingreso(d: Ingreso, user=Depends(auth.requiere("bascula"))):
    cn = user["_cn"]
    mid = uuid_ok(d.id) if d.id else nuevo_id()
    if db.one(cn, "SELECT id FROM dbo.ZTLOGI_BASCULA_MOV WHERE id = ?", mid):
        return {"id": mid}
    c = db.one(cn, "SELECT id, patente, estado FROM dbo.ZTLOGI_CAMIONES WHERE id = ? AND baja = 0 AND alta_estado = 'aprobada'", uuid_ok(d.camion_id))
    if not c:
        raise ApiError(404, "camion", "Camión inexistente")
    if db.one(cn, "SELECT id FROM dbo.ZTLOGI_BASCULA_MOV WHERE camion_id = ? AND salida_en IS NULL", c["id"]):
        raise ApiError(409, "ya_ingreso", "Ese camión ya ingresó y está descargando")
    k = db.one(cn, "SELECT TOP 1 k.id FROM dbo.ZTLOGI_CARGAS k LEFT JOIN dbo.ZTLOGI_BASCULA_MOV b ON b.carga_id = k.id "
                   "WHERE k.camion_id = ? AND k.estado = 'finalizada' AND k.circuito = 'industria' AND b.id IS NULL AND k.jornada >= ? ORDER BY k.fin_en DESC", c["id"], hoy() - dt.timedelta(days=5))
    en = parse_ocurrido(d.ocurrido_en)
    db.run(cn, "INSERT INTO dbo.ZTLOGI_BASCULA_MOV (id, carga_id, camion_id, jornada, ingreso_en, operador_id) VALUES (?,?,?,?,?,?)", mid, k["id"] if k else None, c["id"], en.date(), en, user["id"])
    return {"id": mid, "carga_id": k["id"] if k else None, "ingreso_en": en.strftime("%Y-%m-%dT%H:%M:%S")}


@router.post("/bascula/ingresos/{mid}/salida")
def salida(mid: str, d: Salida | None = None, user=Depends(auth.requiere("bascula"))):
    cn = user["_cn"]
    m = db.one(cn, "SELECT * FROM dbo.ZTLOGI_BASCULA_MOV WHERE id = ?", uuid_ok(mid))
    if not m:
        raise ApiError(404, "movimiento", "Ingreso inexistente")
    if m["salida_en"]:
        return {"id": m["id"], "salida_en": m["salida_en"]}
    en = parse_ocurrido(d.ocurrido_en if d else None)
    ing_dt = dt.datetime.fromisoformat(m["ingreso_en"])
    if en < ing_dt:
        en = max(ahora(), ing_dt + dt.timedelta(minutes=1))
    db.run(cn, "UPDATE dbo.ZTLOGI_BASCULA_MOV SET salida_en = ? WHERE id = ?", en, m["id"])
    c = db.one(cn, "SELECT id, estado FROM dbo.ZTLOGI_CAMIONES WHERE id = ?", m["camion_id"])
    if c and c["estado"] == "ruta":
        db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = 'disponible', updated_at = ? WHERE id = ?", ahora(), c["id"])
    return {"id": m["id"], "salida_en": en.strftime("%Y-%m-%dT%H:%M:%S")}


@router.get("/bascula/historico")
def historico(dias: int = 30, user=Depends(auth.requiere("bascula", "supervisor"))):
    return historico_bascula(user["_cn"], max(1, min(dias, 365)))


def _franja(d: Franja):
    if not hora_valida(d.desde) or not hora_valida(d.hasta):
        raise ApiError(422, "hora", "Indicá el horario de inicio y de fin")
    if mins(d.desde) >= mins(d.hasta):
        raise ApiError(422, "hora", "El horario de fin tiene que ser posterior al de inicio")


@router.post("/bascula/turnos", status_code=201)
def alta_turno(d: Franja, user=Depends(auth.requiere("bascula"))):
    cn = user["_cn"]
    _franja(d)
    tid = uuid_ok(d.id) if d.id else nuevo_id()
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_BASCULA_TURNOS WHERE id = ?", tid):
        db.run(cn, "INSERT INTO dbo.ZTLOGI_BASCULA_TURNOS (id, desde, hasta, creado_por) VALUES (?,?,?,?)", tid, d.desde, d.hasta, user["id"])
    return {"id": tid, "desde": d.desde, "hasta": d.hasta}


@router.delete("/bascula/turnos/{tid}")
def baja_turno(tid: str, user=Depends(auth.requiere("bascula"))):
    db.run(user["_cn"], "DELETE FROM dbo.ZTLOGI_BASCULA_TURNOS WHERE id = ?", uuid_ok(tid))
    return {"ok": True}


@router.post("/bascula/descansos", status_code=201)
def alta_descanso(d: Franja, user=Depends(auth.requiere("bascula"))):
    cn = user["_cn"]
    _franja(d)
    did = uuid_ok(d.id) if d.id else nuevo_id()
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_BASCULA_DESCANSOS WHERE id = ?", did):
        db.run(cn, "INSERT INTO dbo.ZTLOGI_BASCULA_DESCANSOS (id, desde, hasta, motivo, creado_por) VALUES (?,?,?,?,?)", did, d.desde, d.hasta, (d.motivo or "").strip() or None, user["id"])
    return {"id": did, "desde": d.desde, "hasta": d.hasta, "motivo": d.motivo}


@router.delete("/bascula/descansos/{did}")
def baja_descanso(did: str, user=Depends(auth.requiere("bascula"))):
    db.run(user["_cn"], "DELETE FROM dbo.ZTLOGI_BASCULA_DESCANSOS WHERE id = ?", uuid_ok(did))
    return {"ok": True}
