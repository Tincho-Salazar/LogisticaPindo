"""Catálogos administrables: contratistas, destinos, especies, largos. Lectura para todos; escritura jefe/admin."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth, db
from ..util import ApiError, auditar, nuevo_id, uuid_ok

router = APIRouter(tags=["catalogos"])


class Contratista(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)


class Destino(BaseModel):
    nombre: str = Field(min_length=2, max_length=120)
    circuito: str


class Especie(BaseModel):
    nombre: str = Field(min_length=2, max_length=80)


class Largo(BaseModel):
    pies: int = Field(ge=1, le=99)


def leer_catalogos(cn):
    return {
        "contratistas": db.rows(cn, "SELECT id, nombre, activo FROM dbo.ZTLOGI_CONTRATISTAS WHERE activo = 1 ORDER BY nombre"),
        "destinos": db.rows(cn, "SELECT id, nombre, circuito, activo FROM dbo.ZTLOGI_DESTINOS WHERE activo = 1 ORDER BY circuito, nombre"),
        "especies": db.rows(cn, "SELECT id, nombre FROM dbo.ZTLOGI_ESPECIES WHERE activo = 1 ORDER BY nombre"),
        "largos": [r["pies"] for r in db.rows(cn, "SELECT pies FROM dbo.ZTLOGI_LARGOS WHERE activo = 1 ORDER BY pies")],
    }


@router.get("/catalogos")
def catalogos(user=Depends(auth.usuario_actual)):
    return leer_catalogos(user["_cn"])


@router.post("/catalogos/contratistas", status_code=201)
def alta_contratista(d: Contratista, user=Depends(auth.requiere("jefe", "admin"))):
    cn = user["_cn"]
    nombre = " ".join(d.nombre.split())
    ex = db.one(cn, "SELECT id, activo FROM dbo.ZTLOGI_CONTRATISTAS WHERE nombre = ?", nombre)
    if ex:
        if ex["activo"]:
            raise ApiError(409, "duplicado", "Ya existe ese contratista")
        db.run(cn, "UPDATE dbo.ZTLOGI_CONTRATISTAS SET activo = 1 WHERE id = ?", ex["id"])
        return {"id": ex["id"], "nombre": nombre}
    cid = nuevo_id()
    db.run(cn, "INSERT INTO dbo.ZTLOGI_CONTRATISTAS (id, nombre) VALUES (?,?)", cid, nombre)
    auditar(cn, "contratista", cid, "alta", None, {"nombre": nombre}, user, user["_ip"])
    return {"id": cid, "nombre": nombre}


@router.delete("/catalogos/contratistas/{cid}")
def baja_contratista(cid: str, user=Depends(auth.requiere("jefe", "admin"))):
    cn = user["_cn"]
    db.run(cn, "UPDATE dbo.ZTLOGI_CONTRATISTAS SET activo = 0 WHERE id = ?", uuid_ok(cid))
    auditar(cn, "contratista", cid, "baja", None, None, user, user["_ip"])
    return {"ok": True}


@router.post("/catalogos/destinos", status_code=201)
def alta_destino(d: Destino, user=Depends(auth.requiere("jefe", "admin"))):
    cn = user["_cn"]
    if d.circuito not in ("industria", "ventas"):
        raise ApiError(422, "circuito", "El circuito debe ser industria o ventas")
    nombre = " ".join(d.nombre.split())
    ex = db.one(cn, "SELECT id, activo FROM dbo.ZTLOGI_DESTINOS WHERE nombre = ?", nombre)
    if ex:
        if ex["activo"]:
            raise ApiError(409, "duplicado", "Ya existe ese destino")
        db.run(cn, "UPDATE dbo.ZTLOGI_DESTINOS SET activo = 1, circuito = ? WHERE id = ?", d.circuito, ex["id"])
        return {"id": ex["id"], "nombre": nombre, "circuito": d.circuito}
    did = nuevo_id()
    db.run(cn, "INSERT INTO dbo.ZTLOGI_DESTINOS (id, nombre, circuito) VALUES (?,?,?)", did, nombre, d.circuito)
    auditar(cn, "destino", did, "alta", None, {"nombre": nombre, "circuito": d.circuito}, user, user["_ip"])
    return {"id": did, "nombre": nombre, "circuito": d.circuito}


@router.delete("/catalogos/destinos/{did}")
def baja_destino(did: str, user=Depends(auth.requiere("jefe", "admin"))):
    cn = user["_cn"]
    db.run(cn, "UPDATE dbo.ZTLOGI_DESTINOS SET activo = 0 WHERE id = ?", uuid_ok(did))
    auditar(cn, "destino", did, "baja", None, None, user, user["_ip"])
    return {"ok": True}


@router.post("/catalogos/especies", status_code=201)
def alta_especie(d: Especie, user=Depends(auth.requiere("jefe", "admin"))):
    cn = user["_cn"]
    nombre = " ".join(d.nombre.split())
    ex = db.one(cn, "SELECT id FROM dbo.ZTLOGI_ESPECIES WHERE nombre = ?", nombre)
    if ex:
        db.run(cn, "UPDATE dbo.ZTLOGI_ESPECIES SET activo = 1 WHERE id = ?", ex["id"])
        return {"id": ex["id"], "nombre": nombre}
    eid = nuevo_id()
    db.run(cn, "INSERT INTO dbo.ZTLOGI_ESPECIES (id, nombre) VALUES (?,?)", eid, nombre)
    return {"id": eid, "nombre": nombre}


@router.delete("/catalogos/especies/{eid}")
def baja_especie(eid: str, user=Depends(auth.requiere("jefe", "admin"))):
    db.run(user["_cn"], "UPDATE dbo.ZTLOGI_ESPECIES SET activo = 0 WHERE id = ?", uuid_ok(eid))
    return {"ok": True}


@router.post("/catalogos/largos", status_code=201)
def alta_largo(d: Largo, user=Depends(auth.requiere("jefe", "admin"))):
    cn = user["_cn"]
    if db.one(cn, "SELECT pies FROM dbo.ZTLOGI_LARGOS WHERE pies = ?", d.pies):
        db.run(cn, "UPDATE dbo.ZTLOGI_LARGOS SET activo = 1 WHERE pies = ?", d.pies)
    else:
        db.run(cn, "INSERT INTO dbo.ZTLOGI_LARGOS (pies) VALUES (?)", d.pies)
    return {"pies": d.pies}


@router.delete("/catalogos/largos/{pies}")
def baja_largo(pies: int, user=Depends(auth.requiere("jefe", "admin"))):
    db.run(user["_cn"], "UPDATE dbo.ZTLOGI_LARGOS SET activo = 0 WHERE pies = ?", pies)
    return {"ok": True}
