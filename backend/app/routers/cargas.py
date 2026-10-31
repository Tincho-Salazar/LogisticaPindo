"""Cargas: iniciar (camión programado) y finalizar (circuito, rodal, líneas, destino) con descuento de stock en una transacción."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth, consultas as q, db, reglas
from ..util import ApiError, ahora, auditar, hhmm, hoy, nuevo_id, parse_ocurrido, redondear1, uuid_ok

router = APIRouter(tags=["cargas"])


class Iniciar(BaseModel):
    id: str | None = None
    programa_item_id: str
    ocurrido_en: str | None = None


class Linea(BaseModel):
    tipo: str
    largo_pies: int = Field(ge=1, le=99)
    volumen_m3: float = Field(gt=0, le=9999)


class Finalizar(BaseModel):
    circuito: str
    rodal_id: str | None = None
    destino_id: str
    lineas: list[Linea] = Field(min_length=1, max_length=30)
    ocurrido_en: str | None = None


def _carga(cn, kid):
    return db.one(cn, "SELECT * FROM dbo.ZTLOGI_CARGAS WHERE id = ?", uuid_ok(kid))


@router.post("/cargas", status_code=201)
def iniciar(d: Iniciar, user=Depends(auth.requiere("elaborador"))):
    cn = user["_cn"]
    cid = q.contratista_propio(cn, user)
    kid = uuid_ok(d.id) if d.id else nuevo_id()
    if _carga(cn, kid):
        return {"id": kid}
    g = db.one(cn, "SELECT * FROM dbo.ZTLOGI_PROGRAMA WHERE id = ?", uuid_ok(d.programa_item_id))
    if not g or g["contratista_id"] != cid:
        raise ApiError(404, "programa", "Asignación inexistente o de otro contratista")
    if g["estado"] != "programado":
        raise ApiError(409, "estado_programa", "Esa asignación ya no está pendiente")
    c = db.one(cn, "SELECT * FROM dbo.ZTLOGI_CAMIONES WHERE id = ? AND baja = 0", g["camion_id"])
    if not c:
        raise ApiError(404, "camion", "Camión inexistente")
    if q.incidencias_abiertas(cn, {c["id"]}).get(c["id"], {}).get("tipo") == "mecanico":
        raise ApiError(409, "mecanico", "El camión tiene un problema mecánico abierto")
    if c["estado"] not in ("disponible", "vacio", "fila"):
        raise ApiError(409, "estado_camion", f"El camión está {c['estado']} y no puede cargar")
    en = parse_ocurrido(d.ocurrido_en)
    fila_desde = c["fila_desde"] if c["estado"] == "fila" else None
    espera = None
    if fila_desde:
        import datetime as dt
        espera = max(0, int((en - dt.datetime.fromisoformat(fila_desde)).total_seconds() // 60))
    db.run(cn, "INSERT INTO dbo.ZTLOGI_CARGAS (id, camion_id, contratista_id, programa_id, estado, jornada, fila_desde, espera_min, inicio_en, operador_id, operador_nombre) VALUES (?,?,?,?,'en_curso',?,?,?,?,?,?)",
           kid, c["id"], cid, g["id"], en.date(), fila_desde, espera, en, user["id"], user["nombre"])
    db.run(cn, "UPDATE dbo.ZTLOGI_PROGRAMA SET estado = 'cargando', updated_at = ? WHERE id = ?", ahora(), g["id"])
    db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = 'cargando', fila_desde = NULL, fila_contratista_id = NULL, updated_at = ? WHERE id = ?", ahora(), c["id"])
    # Primer inicio real del día del frente: base para "demoras de inicio" (7.11.6)
    if not db.one(cn, "SELECT jornada FROM dbo.ZTLOGI_INICIOS_DIA WHERE jornada = ? AND contratista_id = ?", en.date(), cid):
        ini = db.one(cn, "SELECT hora FROM dbo.ZTLOGI_INICIO_CARGA WHERE jornada = ? AND contratista_id = ?", en.date(), cid)
        plan = ini["hora"] if ini else g["hora"]
        db.run(cn, "INSERT INTO dbo.ZTLOGI_INICIOS_DIA (jornada, contratista_id, hora_plan, hora_real, fuente) VALUES (?,?,?,?,?)", en.date(), cid, plan, hhmm(en), "elaborador" if ini else "programa")
    return {"id": kid, "inicio_en": en.strftime("%Y-%m-%dT%H:%M:%S"), "espera_min": espera}


@router.post("/cargas/{kid}/finalizar")
def finalizar(kid: str, d: Finalizar, user=Depends(auth.requiere("elaborador"))):
    cn = user["_cn"]
    cid = q.contratista_propio(cn, user)
    k = _carga(cn, kid)
    if not k or k["contratista_id"] != cid:
        raise ApiError(404, "carga", "Carga inexistente o de otro contratista")
    if k["estado"] == "finalizada":
        return {"id": k["id"], "estado": "finalizada"}  # idempotente
    if d.circuito not in ("industria", "ventas"):
        raise ApiError(422, "circuito", "Indicá si el despacho es para industria propia o ventas")
    dest = db.one(cn, "SELECT id, circuito FROM dbo.ZTLOGI_DESTINOS WHERE id = ? AND activo = 1", uuid_ok(d.destino_id))
    if not dest or dest["circuito"] != d.circuito:
        raise ApiError(422, "destino", "El destino no pertenece a ese circuito")
    rodal_id = None
    if d.rodal_id:
        r = db.one(cn, "SELECT id FROM dbo.ZTLOGI_RODALES WHERE id = ? AND contratista_id = ? AND activo = 1", uuid_ok(d.rodal_id), cid)
        if not r:
            raise ApiError(422, "rodal", "El rodal no pertenece a este contratista")
        rodal_id = r["id"]
    elif db.one(cn, "SELECT TOP 1 id FROM dbo.ZTLOGI_RODALES WHERE contratista_id = ? AND activo = 1", cid):
        raise ApiError(422, "rodal", "Elegí el rodal de carga")
    for l in d.lineas:
        if l.tipo not in ("fino", "grueso"):
            raise ApiError(422, "tipo", "Tipo inválido")
    lineas = [{"tipo": l.tipo, "largo_pies": l.largo_pies, "volumen_m3": redondear1(l.volumen_m3)} for l in d.lineas]
    # Bloqueo de las pilas del contratista para que dos finalizaciones simultáneas no vendan el mismo stock
    pilas = db.rows(cn, "SELECT id, tipo, largo_pies, uso, volumen_m3 FROM dbo.ZTLOGI_PILAS WITH (UPDLOCK, HOLDLOCK) WHERE contratista_id = ? AND eliminada = 0", cid)
    try:
        nuevos = reglas.descontar_stock(pilas, lineas, d.circuito)
    except reglas.StockInsuficiente as e:
        det = e.detalle
        raise ApiError(409, "stock_insuficiente", f"Solo hay {det['disponible']:.1f} m³ de rollo {det['tipo']} de {det['largo_pies']} pies" + (" (stock Pindó SA)" if d.circuito == "industria" else ""), det)
    en = parse_ocurrido(d.ocurrido_en)
    import datetime as dt
    ini_dt = dt.datetime.fromisoformat(k["inicio_en"])
    if en < ini_dt:
        en = max(ahora(), ini_dt + dt.timedelta(minutes=1))
    for pid, vol in nuevos.items():
        db.run(cn, "UPDATE dbo.ZTLOGI_PILAS SET volumen_m3 = ?, updated_at = ? WHERE id = ?", vol, ahora(), pid)
        p = next(x for x in pilas if x["id"] == pid)
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PILAS_HIST (pila_id, contratista_id, tipo, largo_pies, uso, volumen_m3, accion, relevado_por, en) VALUES (?,?,?,?,?,?,'descuento',?,?)",
               pid, cid, p["tipo"], p["largo_pies"], p["uso"], vol, user["nombre"], en)
    for l in lineas:
        db.run(cn, "INSERT INTO dbo.ZTLOGI_CARGA_LINEAS (carga_id, tipo, largo_pies, volumen_m3) VALUES (?,?,?,?)", k["id"], l["tipo"], l["largo_pies"], l["volumen_m3"])
    db.run(cn, "UPDATE dbo.ZTLOGI_CARGAS SET estado = 'finalizada', circuito = ?, rodal_id = ?, destino_id = ?, fin_en = ?, jornada = ?, version = version + 1 WHERE id = ?",
           d.circuito, rodal_id, dest["id"], en, en.date(), k["id"])
    db.run(cn, "UPDATE dbo.ZTLOGI_CAMIONES SET estado = 'ruta', updated_at = ? WHERE id = ?", ahora(), k["camion_id"])
    if k["programa_id"]:
        db.run(cn, "UPDATE dbo.ZTLOGI_PROGRAMA SET estado = 'cumplido', updated_at = ? WHERE id = ?", ahora(), k["programa_id"])
    auditar(cn, "carga", k["id"], "finalizar", {"estado": "en_curso"}, {"circuito": d.circuito, "destino_id": dest["id"], "rodal_id": rodal_id, "lineas": lineas}, user, user["_ip"])
    return {"id": k["id"], "estado": "finalizada", "fin_en": en.strftime("%Y-%m-%dT%H:%M:%S"), "total_m3": redondear1(sum(l["volumen_m3"] for l in lineas))}


@router.get("/cargas")
def listar(jornada: str | None = None, contratista_id: str | None = None, user=Depends(auth.requiere("supervisor", "elaborador", "jefe", "bascula"))):
    from ..util import jornada_de
    cn = user["_cn"]
    j = jornada_de(jornada)
    cid = contratista_id
    if auth.tiene_rol(user, "elaborador") and not auth.tiene_rol(user, "supervisor", "bascula"):
        cid = q.contratista_propio(cn, user, contratista_id, permitir_jefe_lectura=True)
    return [k for k in q.cargas_desde(cn, j, contratista_id=uuid_ok(cid) if cid else None) if k["jornada"] == j.isoformat() or k["estado"] == "en_curso"]
