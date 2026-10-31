"""Tarifario (solo Jefe de Área Forestal y admin): rodales, tarifas con historial de vigencia e importación desde planilla."""
import csv
import datetime as dt
import io

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field

from .. import auth, consultas as q, db, reglas
from ..util import ApiError, ahora, auditar, hoy, nuevo_id, redondear1, uuid_ok

router = APIRouter(tags=["tarifario"])
JEFE = auth.requiere("jefe", "admin")


class Rodal(BaseModel):
    id: str | None = None
    codigo: str = Field(min_length=2, max_length=30)
    contratista_id: str


class Tarifa(BaseModel):
    km_asfalto: float = Field(ge=0, le=9999)
    km_tierra: float = Field(ge=0, le=9999)
    tarifa_4x2: int = Field(ge=0, le=999999999)
    tarifa_6x4: int = Field(ge=0, le=999999999)


@router.get("/rodales")
def rodales(user=Depends(JEFE)):
    cn = user["_cn"]
    rs = q.rodales(cn)
    tar = q.tarifas_vigentes(cn)
    for r in rs:
        r["tarifas"] = [t for t in tar if t["rodal_id"] == r["id"]]
    return rs


@router.post("/rodales", status_code=201)
def alta_rodal(d: Rodal, user=Depends(JEFE)):
    cn = user["_cn"]
    cod = reglas.normalizar_rodal(d.codigo)
    if not cod:
        raise ApiError(422, "codigo", "Ingresá el código del rodal")
    cid = uuid_ok(d.contratista_id)
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE id = ? AND activo = 1", cid):
        raise ApiError(422, "contratista", "Contratista inexistente")
    ex = db.one(cn, "SELECT id, activo FROM dbo.ZTLOGI_RODALES WHERE codigo = ?", cod)
    if ex and ex["activo"]:
        raise ApiError(409, "rodal_existente", f"Ya existe el rodal {cod}")
    if ex:
        db.run(cn, "UPDATE dbo.ZTLOGI_RODALES SET activo = 1, contratista_id = ? WHERE id = ?", cid, ex["id"])
        rid = ex["id"]
    else:
        rid = uuid_ok(d.id) if d.id else nuevo_id()
        db.run(cn, "INSERT INTO dbo.ZTLOGI_RODALES (id, codigo, contratista_id) VALUES (?,?,?)", rid, cod, cid)
    auditar(cn, "rodal", rid, "alta", None, {"codigo": cod, "contratista_id": cid}, user, user["_ip"])
    return {"id": rid, "codigo": cod, "contratista_id": cid}


@router.delete("/rodales/{rid}")
def baja_rodal(rid: str, user=Depends(JEFE)):
    cn = user["_cn"]
    r = db.one(cn, "SELECT * FROM dbo.ZTLOGI_RODALES WHERE id = ?", uuid_ok(rid))
    if r:
        _cerrar_vigencias(cn, r["id"], None)
        db.run(cn, "UPDATE dbo.ZTLOGI_RODALES SET activo = 0 WHERE id = ?", r["id"])
        auditar(cn, "rodal", r["id"], "baja", r, None, user, user["_ip"])
    return {"ok": True}


def _cerrar_vigencias(cn, rodal_id, destino_id):
    """Cierra la tarifa vigente: si empezó hoy y ningún remito la usa se borra; si no se le pone vigente_hasta = ayer."""
    ayer = hoy() - dt.timedelta(days=1)
    sql_w = "rodal_id = ? AND vigente_hasta IS NULL" + (" AND destino_id = ?" if destino_id else "")
    params = [rodal_id] + ([destino_id] if destino_id else [])
    db.run(cn, f"DELETE FROM dbo.ZTLOGI_TARIFAS WHERE {sql_w} AND vigente_desde >= ? AND id NOT IN (SELECT tarifa_id FROM dbo.ZTLOGI_REMITOS WHERE tarifa_id IS NOT NULL)", *params, hoy())
    db.run(cn, f"UPDATE dbo.ZTLOGI_TARIFAS SET vigente_hasta = ? WHERE {sql_w}", ayer, *params)


def guardar_tarifa(cn, user, rodal_id, destino_id, d: Tarifa):
    if d.tarifa_4x2 <= 0 and d.tarifa_6x4 <= 0:
        raise ApiError(422, "tarifa", "Cargá al menos una tarifa (4x2 o 6x4) mayor a cero")
    antes = q.tarifa_vigente(cn, rodal_id, destino_id, hoy())
    _cerrar_vigencias(cn, rodal_id, destino_id)
    tid = nuevo_id()
    db.run(cn, "INSERT INTO dbo.ZTLOGI_TARIFAS (id, rodal_id, destino_id, km_asfalto, km_tierra, tarifa_4x2, tarifa_6x4, vigente_desde, creado_por) VALUES (?,?,?,?,?,?,?,?,?)",
           tid, rodal_id, destino_id, redondear1(d.km_asfalto), redondear1(d.km_tierra), d.tarifa_4x2, d.tarifa_6x4, hoy(), user["id"])
    auditar(cn, "tarifa", tid, "vigencia", antes, {"rodal_id": rodal_id, "destino_id": destino_id, **d.model_dump()}, user, user["_ip"])
    return db.one(cn, "SELECT id, rodal_id, destino_id, km_asfalto, km_tierra, tarifa_4x2, tarifa_6x4, vigente_desde FROM dbo.ZTLOGI_TARIFAS WHERE id = ?", tid)


@router.put("/rodales/{rid}/tarifas/{did}")
def poner_tarifa(rid: str, did: str, d: Tarifa, user=Depends(JEFE)):
    cn = user["_cn"]
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_RODALES WHERE id = ? AND activo = 1", uuid_ok(rid)):
        raise ApiError(404, "rodal", "Rodal inexistente")
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_DESTINOS WHERE id = ? AND activo = 1", uuid_ok(did)):
        raise ApiError(404, "destino", "Destino inexistente")
    return guardar_tarifa(cn, user, rid, did, d)


@router.delete("/rodales/{rid}/tarifas/{did}")
def quitar_tarifa(rid: str, did: str, user=Depends(JEFE)):
    cn = user["_cn"]
    _cerrar_vigencias(cn, uuid_ok(rid), uuid_ok(did))
    auditar(cn, "tarifa", f"{rid}/{did}", "cierre", None, None, user, user["_ip"])
    return {"ok": True}


@router.get("/tarifas")
def tarifas(rodal_id: str | None = None, destino_id: str | None = None, user=Depends(auth.requiere("jefe", "admin", "transportista"))):
    cn = user["_cn"]
    rs = q.tarifas_vigentes(cn)
    if rodal_id:
        rs = [t for t in rs if t["rodal_id"] == uuid_ok(rodal_id)]
    if destino_id:
        rs = [t for t in rs if t["destino_id"] == uuid_ok(destino_id)]
    return rs


# ---------- importación desde planilla (Empresa, Rodal, Destino, Km asfalto, Km tierra, 4x2, 6x4) ----------

COLS = {"empresa": "empresa", "rodal": "rodal", "destino": "destino", "km asfalto": "km_asfalto", "kmasfalto": "km_asfalto", "km tierra": "km_tierra", "kmtierra": "km_tierra", "4x2": "t42", "6x4": "t64"}


def _num(v):
    if v is None or v == "":
        return 0.0
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace("$", "").replace(" ", "")
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    return float(s)


def _leer_planilla(nombre, data):
    if nombre.lower().endswith(".xlsx"):
        from openpyxl import load_workbook
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
        ws = wb.active
        filas = [[c for c in r] for r in ws.iter_rows(values_only=True)]
    elif nombre.lower().endswith(".csv"):
        txt = data.decode("utf-8-sig", errors="replace")
        dialect = csv.Sniffer().sniff(txt[:2000], delimiters=";,\t") if txt.strip() else csv.excel
        filas = list(csv.reader(io.StringIO(txt), dialect))
    else:
        raise ApiError(422, "formato", "Subí un archivo .xlsx o .csv")
    filas = [f for f in filas if any(c not in (None, "") for c in f)]
    if not filas:
        raise ApiError(422, "vacio", "La planilla está vacía")
    cab = [COLS.get(str(c or "").strip().lower(), None) for c in filas[0]]
    faltan = [k for k in ("rodal", "destino", "t42", "t64") if k not in cab]
    if faltan:
        raise ApiError(422, "columnas", "Faltan columnas en la planilla: Empresa, Rodal, Destino, Km asfalto, Km tierra, 4x2, 6x4")
    out = []
    for i, f in enumerate(filas[1:], start=2):
        d = {cab[j]: f[j] for j in range(min(len(cab), len(f))) if cab[j]}
        d["fila"] = i
        out.append(d)
    return out


@router.post("/tarifas/importar")
def importar(modo: str = "previsualizar", archivo: UploadFile = File(...), user=Depends(JEFE)):
    cn = user["_cn"]
    if modo not in ("previsualizar", "confirmar"):
        raise ApiError(422, "modo", "modo debe ser previsualizar o confirmar")
    data = archivo.file.read()
    if len(data) > 5 * 1024 * 1024:
        raise ApiError(413, "tamano", "La planilla supera los 5 MB")
    filas = _leer_planilla(archivo.filename or "", data)
    contrs = {c["nombre"].strip().lower(): c for c in db.rows(cn, "SELECT id, nombre FROM dbo.ZTLOGI_CONTRATISTAS WHERE activo = 1")}
    dests = {d["nombre"].strip().lower(): d for d in db.rows(cn, "SELECT id, nombre, circuito FROM dbo.ZTLOGI_DESTINOS WHERE activo = 1")}
    rods = {r["codigo"]: r for r in db.rows(cn, "SELECT id, codigo, contratista_id FROM dbo.ZTLOGI_RODALES WHERE activo = 1")}
    validas, errores, rodales_nuevos = [], [], []
    for f in filas:
        cod = reglas.normalizar_rodal(f.get("rodal"))
        emp = str(f.get("empresa") or "").strip()
        des = str(f.get("destino") or "").strip()
        try:
            ka, kt, t42, t64 = _num(f.get("km_asfalto")), _num(f.get("km_tierra")), _num(f.get("t42")), _num(f.get("t64"))
        except ValueError:
            errores.append({"fila": f["fila"], "error": "Valor numérico inválido"})
            continue
        if not cod:
            errores.append({"fila": f["fila"], "error": "Falta el rodal"})
            continue
        d = dests.get(des.lower())
        if not d:
            errores.append({"fila": f["fila"], "error": f"Destino desconocido: {des}. Crealo primero en catálogos con su circuito."})
            continue
        r = rods.get(cod)
        c = contrs.get(emp.lower())
        if not r:
            if not c:
                errores.append({"fila": f["fila"], "error": f"Rodal nuevo {cod} sin empresa conocida: {emp or '(vacía)'}"})
                continue
            if cod not in rodales_nuevos:
                rodales_nuevos.append(cod)
        if t42 <= 0 and t64 <= 0:
            errores.append({"fila": f["fila"], "error": "Sin tarifa 4x2 ni 6x4"})
            continue
        validas.append({"fila": f["fila"], "rodal": cod, "rodal_id": r["id"] if r else None, "contratista_id": (r["contratista_id"] if r else c["id"]), "empresa": emp,
                        "destino": d["nombre"], "destino_id": d["id"], "km_asfalto": redondear1(ka), "km_tierra": redondear1(kt), "tarifa_4x2": int(round(t42)), "tarifa_6x4": int(round(t64))})
    res = {"modo": modo, "validas": validas, "errores": errores, "rodales_nuevos": rodales_nuevos, "aplicadas": 0}
    if modo == "confirmar" and validas:
        for v in validas:
            if not v["rodal_id"]:
                rid = nuevo_id()
                db.run(cn, "INSERT INTO dbo.ZTLOGI_RODALES (id, codigo, contratista_id) VALUES (?,?,?)", rid, v["rodal"], v["contratista_id"])
                for w in validas:
                    if w["rodal"] == v["rodal"]:
                        w["rodal_id"] = rid
            guardar_tarifa(cn, user, v["rodal_id"], v["destino_id"], Tarifa(km_asfalto=v["km_asfalto"], km_tierra=v["km_tierra"], tarifa_4x2=v["tarifa_4x2"], tarifa_6x4=v["tarifa_6x4"]))
        res["aplicadas"] = len(validas)
        auditar(cn, "tarifa", None, "importacion", None, {"filas": len(validas), "rodales_nuevos": rodales_nuevos}, user, user["_ip"])
    return res
