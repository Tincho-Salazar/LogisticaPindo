"""Remitos de flete: foto + lectura por IA (borrador), confirmación con revisión humana, listado, foto, baja, facturación y PDF."""
import datetime as dt
import hashlib
import hmac
import io
import time

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps
from pydantic import BaseModel, Field

from .. import auth, config, consultas as q, db, ocr, reglas, reportes
from ..util import ApiError, ahora, auditar, hoy, nuevo_id, parse_ocurrido, redondear1, uuid_ok

router = APIRouter(tags=["remitos"])
MAX_FOTO = 10 * 1024 * 1024


class Remito(BaseModel):
    id: str | None = None
    camion_id: str
    carga_id: str | None = None
    borrador_id: str | None = None
    numero: str | None = Field(default=None, max_length=30)
    fecha: str | None = None
    rodal_id: str
    destino_id: str | None = None
    toneladas: float = Field(gt=0, le=200)
    ocurrido_en: str | None = None


class RemitoEdicion(BaseModel):
    carga_id: str | None = None
    numero: str | None = Field(default=None, max_length=30)
    fecha: str | None = None
    rodal_id: str
    destino_id: str | None = None
    toneladas: float = Field(gt=0, le=200)


def _firma(rid, exp):
    return hmac.new(config.JWT_SECRET.encode(), f"foto:{rid}:{exp}".encode(), hashlib.sha256).hexdigest()[:32]


def foto_url(rid, mini=False):
    exp = int(time.time()) + 600
    return f"/api/v1/remitos/{rid}/foto?t={_firma(rid, exp)}&e={exp}" + ("&mini=1" if mini else "")


def _guardar_fotos(data):
    """Verifica que sea una imagen real, la normaliza a JPEG (lado largo 1600) y genera la miniatura (400)."""
    try:
        im = Image.open(io.BytesIO(data))
        im.verify()
        im = Image.open(io.BytesIO(data))
        if im.format not in ("JPEG", "PNG", "WEBP"):
            raise ValueError(im.format)
        im = ImageOps.exif_transpose(im).convert("RGB")
    except Exception:
        raise ApiError(415, "imagen", "La foto no es una imagen válida (JPEG, PNG o WebP)")
    config.FOTOS_DIR.mkdir(parents=True, exist_ok=True)
    base = nuevo_id()
    grande = im.copy()
    grande.thumbnail((1600, 1600))
    p1 = config.FOTOS_DIR / f"{base}.jpg"
    grande.save(p1, "JPEG", quality=80, optimize=True)
    mini = im.copy()
    mini.thumbnail((400, 400))
    p2 = config.FOTOS_DIR / f"{base}_mini.jpg"
    mini.save(p2, "JPEG", quality=75)
    return p1.name, p2.name, p1.read_bytes()


def _match_rodal(cn, texto):
    n = reglas.normalizar_rodal(texto)
    if not n:
        return None
    r = next((r for r in q.rodales(cn) if reglas.normalizar_rodal(r["codigo"]) == n), None)
    return r["id"] if r else None


def _match_destino(cn, texto):
    t = (texto or "").strip().lower()
    if not t:
        return None
    ds = db.rows(cn, "SELECT id, nombre FROM dbo.ZTLOGI_DESTINOS WHERE activo = 1")
    for d in ds:
        n = d["nombre"].lower()
        if n == t or n in t or t in n:
            return d["id"]
    return None


@router.post("/remitos/foto", status_code=201)
def subir_foto(camion_id: str, archivo: UploadFile = File(...), user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, camion_id)
    data = archivo.file.read()
    if len(data) > MAX_FOTO:
        raise ApiError(413, "tamano", "La foto supera los 10 MB")
    foto, mini, jpeg = _guardar_fotos(data)
    bid = nuevo_id()
    db.run(cn, "INSERT INTO dbo.ZTLOGI_REMITO_BORRADORES (id, camion_id, usuario_id, foto_path, foto_mini_path, estado_ocr, creado_en) VALUES (?,?,?,?,?,'pendiente',?)", bid, c["id"], user["id"], foto, mini, ahora())
    datos, crudo, estado = None, None, "fallido"
    usados = db.scalar(cn, "SELECT COUNT(*) FROM dbo.ZTLOGI_REMITO_BORRADORES WHERE usuario_id = ? AND creado_en >= ? AND estado_ocr <> 'sin_cupo'", user["id"], dt.datetime.combine(hoy(), dt.time()))
    if not ocr.disponible():
        estado = "sin_api"
    elif usados > config.VISION_DAILY_LIMIT_PER_USER:
        estado = "sin_cupo"
    else:
        cn.commit()  # el borrador queda guardado aunque la lectura tarde o falle
        rod = [r["codigo"] for r in q.rodales(cn)]
        des = [d["nombre"] for d in db.rows(cn, "SELECT nombre FROM dbo.ZTLOGI_DESTINOS WHERE activo = 1")]
        leido, crudo = ocr.leer_remito(jpeg, rod, des)
        if leido:
            estado = "leido"
            datos = {"numero": leido["numero"], "fecha": leido["fecha"], "rodal_id": _match_rodal(cn, leido["rodal"]), "destino_id": _match_destino(cn, leido["destino"]),
                     "toneladas": leido["toneladas"], "patente_leida": leido["patente"]}
    db.run(cn, "UPDATE dbo.ZTLOGI_REMITO_BORRADORES SET estado_ocr = ?, ocr_json = ? WHERE id = ?", estado, crudo, bid)
    return {"borrador_id": bid, "estado_ocr": estado, "datos": datos, "foto_url": _borrador_url(bid)}


def _borrador_url(bid):
    exp = int(time.time()) + 600
    return f"/api/v1/remitos/borradores/{bid}/foto?t={_firma(bid, exp)}&e={exp}"


def _verificar_firma(rid, t, e):
    try:
        e = int(e)
    except (TypeError, ValueError):
        raise ApiError(403, "firma", "Enlace inválido")
    if e < time.time() or not hmac.compare_digest(_firma(rid, e), t or ""):
        raise ApiError(403, "firma", "Enlace vencido")


@router.get("/remitos/borradores/{bid}/foto")
def foto_borrador(bid: str, t: str = "", e: str = "", cn=Depends(auth.conn)):
    bid = uuid_ok(bid)
    _verificar_firma(bid, t, e)
    b = db.one(cn, "SELECT foto_path FROM dbo.ZTLOGI_REMITO_BORRADORES WHERE id = ?", bid)
    if not b:
        raise ApiError(404, "foto", "Foto inexistente")
    return FileResponse(config.FOTOS_DIR / b["foto_path"], media_type="image/jpeg", headers={"Cache-Control": "private, max-age=600"})


def _vincular_carga(cn, camion_id, rodal_id, destino_id, fecha, carga_id_explicito=None):
    if carga_id_explicito:
        k = db.one(cn, "SELECT id FROM dbo.ZTLOGI_CARGAS WHERE id = ? AND camion_id = ? AND estado = 'finalizada'", uuid_ok(carga_id_explicito), camion_id)
        if k:
            return k["id"]
    # Auto-asociación inteligente: busca la carga finalizada del camión sin remito asociado en la misma fecha o últimos 3 días
    sql = ("SELECT TOP 1 k.id FROM dbo.ZTLOGI_CARGAS k "
           "LEFT JOIN dbo.ZTLOGI_REMITOS r ON r.carga_id = k.id AND r.eliminado = 0 "
           "WHERE k.camion_id = ? AND k.estado = 'finalizada' AND r.id IS NULL AND k.jornada BETWEEN ? AND ? "
           "ORDER BY CASE WHEN k.rodal_id = ? THEN 0 ELSE 1 END, CASE WHEN k.destino_id = ? THEN 0 ELSE 1 END, ABS(DATEDIFF(day, k.jornada, ?)), k.fin_en DESC")
    k = db.one(cn, sql, camion_id, fecha - dt.timedelta(days=3), fecha + dt.timedelta(days=1), rodal_id, destino_id, fecha)
    return k["id"] if k else None


@router.post("/remitos", status_code=201)
def confirmar(d: Remito, user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, d.camion_id)
    rid = uuid_ok(d.id) if d.id else nuevo_id()
    if db.one(cn, "SELECT id FROM dbo.ZTLOGI_REMITOS WHERE id = ?", rid):
        return _remito(cn, rid)
    rod = db.one(cn, "SELECT id FROM dbo.ZTLOGI_RODALES WHERE id = ? AND activo = 1", uuid_ok(d.rodal_id))
    if not rod:
        raise ApiError(422, "rodal", "Elegí el rodal (punto de carga) del remito")
    did = None
    if d.destino_id:
        dest = db.one(cn, "SELECT id FROM dbo.ZTLOGI_DESTINOS WHERE id = ? AND activo = 1", uuid_ok(d.destino_id))
        if not dest:
            raise ApiError(422, "destino", "Destino inválido")
        did = dest["id"]
    try:
        fecha = dt.date.fromisoformat(d.fecha) if d.fecha else hoy()
    except ValueError:
        raise ApiError(422, "fecha", "Fecha inválida")
    if fecha > hoy() + dt.timedelta(days=1) or fecha < hoy() - dt.timedelta(days=400):
        raise ApiError(422, "fecha", "La fecha del remito está fuera de rango")
    numero = (d.numero or "").strip() or None
    if numero and db.one(cn, "SELECT id FROM dbo.ZTLOGI_REMITOS WHERE camion_id = ? AND numero = ? AND eliminado = 0", c["id"], numero):
        ex = db.one(cn, "SELECT id FROM dbo.ZTLOGI_REMITOS WHERE camion_id = ? AND numero = ? AND eliminado = 0", c["id"], numero)
        raise ApiError(409, "remito_duplicado", f"Ya cargaste un remito con el número {numero}", {"remito_id": ex["id"]})
    foto = mini = None
    origen = "manual"
    if d.borrador_id:
        b = db.one(cn, "SELECT * FROM dbo.ZTLOGI_REMITO_BORRADORES WHERE id = ? AND usuario_id = ?", uuid_ok(d.borrador_id), user["id"])
        if b:
            foto, mini = b["foto_path"], b["foto_mini_path"]
            origen = "ocr" if b["estado_ocr"] == "leido" else "manual"
            db.run(cn, "DELETE FROM dbo.ZTLOGI_REMITO_BORRADORES WHERE id = ?", b["id"])
    tn = redondear1(d.toneladas)
    tarifa = q.tarifa_vigente(cn, rod["id"], did, fecha)
    tarifa_unit = reglas.importe_remito(tarifa, c["traccion"], 1.0)
    importe = reglas.importe_remito(tarifa, c["traccion"], tn)
    carga_id = _vincular_carga(cn, c["id"], rod["id"], did, fecha, d.carga_id)
    en = parse_ocurrido(d.ocurrido_en)
    db.run(cn, "INSERT INTO dbo.ZTLOGI_REMITOS (id, camion_id, carga_id, numero, fecha, rodal_id, destino_id, toneladas, foto_path, foto_mini_path, origen_dato, tarifa_id, tarifa_aplicada, importe, cargado_por, usuario_id, cargado_en) "
               "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
           rid, c["id"], carga_id, numero, fecha, rod["id"], did, tn, foto, mini, origen, tarifa["id"] if tarifa else None, tarifa_unit, importe, user["nombre"], user["id"], en)
    auditar(cn, "remito", rid, "alta", None, d.model_dump() | {"importe": importe, "tarifa_aplicada": tarifa_unit, "carga_id": carga_id}, user, user["_ip"])
    return _remito(cn, rid)


@router.put("/remitos/{rid}")
def editar(rid: str, d: RemitoEdicion, user=Depends(auth.requiere("transportista", "supervisor"))):
    cn = user["_cn"]
    rid = uuid_ok(rid)
    r = db.one(cn, "SELECT * FROM dbo.ZTLOGI_REMITOS WHERE id = ? AND eliminado = 0", rid)
    if not r:
        raise ApiError(404, "remito", "Remito inexistente")
    if not auth.tiene_rol(user, "supervisor"):
        c = q.camion_propio(cn, user, r["camion_id"])
    else:
        c = db.one(cn, f"SELECT {q.CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.id = ?", r["camion_id"])
    rod = db.one(cn, "SELECT id FROM dbo.ZTLOGI_RODALES WHERE id = ? AND activo = 1", uuid_ok(d.rodal_id))
    if not rod:
        raise ApiError(422, "rodal", "Elegí el rodal (punto de carga) del remito")
    did = None
    if d.destino_id:
        dest = db.one(cn, "SELECT id FROM dbo.ZTLOGI_DESTINOS WHERE id = ? AND activo = 1", uuid_ok(d.destino_id))
        if not dest:
            raise ApiError(422, "destino", "Destino inválido")
        did = dest["id"]
    try:
        fecha = dt.date.fromisoformat(d.fecha) if d.fecha else dt.date.fromisoformat(r["fecha"])
    except ValueError:
        raise ApiError(422, "fecha", "Fecha inválida")
    if fecha > hoy() + dt.timedelta(days=1) or fecha < hoy() - dt.timedelta(days=400):
        raise ApiError(422, "fecha", "La fecha del remito está fuera de rango")
    numero = (d.numero or "").strip() or None
    if numero:
        ex = db.one(cn, "SELECT id FROM dbo.ZTLOGI_REMITOS WHERE camion_id = ? AND numero = ? AND eliminado = 0 AND id <> ?", c["id"], numero, rid)
        if ex:
            raise ApiError(409, "remito_duplicado", f"Ya existe un remito con el número {numero}", {"remito_id": ex["id"]})
    tn = redondear1(d.toneladas)
    tarifa = q.tarifa_vigente(cn, rod["id"], did, fecha)
    tarifa_unit = reglas.importe_remito(tarifa, c["traccion"], 1.0)
    importe = reglas.importe_remito(tarifa, c["traccion"], tn)
    carga_id = _vincular_carga(cn, c["id"], rod["id"], did, fecha, d.carga_id or r.get("carga_id"))
    antes = {k: r.get(k) for k in ("numero", "fecha", "rodal_id", "destino_id", "toneladas", "tarifa_aplicada", "importe", "carga_id")}
    db.run(cn, "UPDATE dbo.ZTLOGI_REMITOS SET carga_id = ?, numero = ?, fecha = ?, rodal_id = ?, destino_id = ?, toneladas = ?, tarifa_id = ?, tarifa_aplicada = ?, importe = ? WHERE id = ?",
           carga_id, numero, fecha, rod["id"], did, tn, tarifa["id"] if tarifa else None, tarifa_unit, importe, rid)
    auditar(cn, "remito", rid, "edicion", antes, d.model_dump() | {"importe": importe, "tarifa_aplicada": tarifa_unit, "carga_id": carga_id}, user, user["_ip"])
    return _remito(cn, rid)


def _remito(cn, rid):
    r = db.one(cn, "SELECT r.id, r.camion_id, r.carga_id, r.numero, r.fecha, r.rodal_id, ro.codigo AS rodal, r.destino_id, d.nombre AS destino, r.toneladas, r.origen_dato, r.tarifa_aplicada, r.importe, r.cargado_por, r.cargado_en, r.foto_path "
                   "FROM dbo.ZTLOGI_REMITOS r JOIN dbo.ZTLOGI_RODALES ro ON ro.id = r.rodal_id LEFT JOIN dbo.ZTLOGI_DESTINOS d ON d.id = r.destino_id WHERE r.id = ? AND r.eliminado = 0", rid)
    if not r:
        raise ApiError(404, "remito", "Remito inexistente")
    r["foto"] = bool(r.pop("foto_path"))
    if r["foto"]:
        r["foto_url"] = foto_url(r["id"])
        r["foto_mini_url"] = foto_url(r["id"], mini=True)
    return r


@router.get("/remitos/{rid}")
def detalle(rid: str, user=Depends(auth.requiere("transportista", "jefe", "supervisor"))):
    cn = user["_cn"]
    r = _remito(cn, uuid_ok(rid))
    if not auth.tiene_rol(user, "supervisor"):
        q.camion_propio(cn, user, r["camion_id"], permitir_jefe_lectura=True)
    return r


@router.get("/remitos/{rid}/foto")
def foto(rid: str, t: str = "", e: str = "", mini: str = "", cn=Depends(auth.conn)):
    rid = uuid_ok(rid)
    _verificar_firma(rid, t, e)
    r = db.one(cn, "SELECT foto_path, foto_mini_path FROM dbo.ZTLOGI_REMITOS WHERE id = ?", rid)
    if not r or not r["foto_path"]:
        raise ApiError(404, "foto", "Sin foto")
    p = config.FOTOS_DIR / (r["foto_mini_path"] if mini else r["foto_path"])
    if not p.exists():
        raise ApiError(404, "foto", "Sin foto")
    return FileResponse(p, media_type="image/jpeg", headers={"Cache-Control": "private, max-age=600"})


@router.delete("/remitos/{rid}")
def borrar(rid: str, user=Depends(auth.requiere("transportista"))):
    cn = user["_cn"]
    r = db.one(cn, "SELECT * FROM dbo.ZTLOGI_REMITOS WHERE id = ? AND eliminado = 0", uuid_ok(rid))
    if not r:
        return {"ok": True}
    q.camion_propio(cn, user, r["camion_id"])
    db.run(cn, "UPDATE dbo.ZTLOGI_REMITOS SET eliminado = 1 WHERE id = ?", r["id"])
    auditar(cn, "remito", r["id"], "baja", {k: r[k] for k in ("numero", "fecha", "rodal_id", "destino_id", "toneladas", "importe")}, None, user, user["_ip"])
    return {"ok": True}


@router.get("/camiones/{cid}/facturacion")
def facturacion(cid: str, user=Depends(auth.requiere("transportista", "jefe"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid, permitir_jefe_lectura=True)
    return reportes.datos_fletes(cn, c)


@router.get("/camiones/{cid}/reportes/fletes.pdf")
def pdf_fletes(cid: str, user=Depends(auth.requiere("transportista", "jefe"))):
    cn = user["_cn"]
    c = q.camion_propio(cn, user, cid, permitir_jefe_lectura=True)
    pdf = reportes.pdf_fletes(reportes.datos_fletes(cn, c))
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="Fletes-{reglas.patente_norm(c["patente"])}-{hoy().isoformat()}.pdf"'})
