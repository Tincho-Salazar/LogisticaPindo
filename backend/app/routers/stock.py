"""Relevamiento de stock en pila (elaborador; supervisor por excepción) y reporte PDF de stock."""
from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .. import auth, config, consultas as q, db, reportes
from ..util import ApiError, ahora, auditar, cierre_pasado, hhmm, nuevo_id, parse_ocurrido, redondear1, uuid_ok

router = APIRouter(tags=["stock"])


class Pila(BaseModel):
    id: str | None = None
    contratista_id: str | None = None
    especie_id: str
    tipo: str
    largo_pies: int = Field(ge=1, le=99)
    volumen_m3: float = Field(ge=0, le=999999)
    uso: str = "pindo"
    relevado_por: str | None = Field(default=None, max_length=120)
    hora: str | None = None
    ocurrido_en: str | None = None


def _contratista_para(cn, user, pedido):
    if auth.tiene_rol(user, "elaborador") and user.get("contratista_id") and not auth.tiene_rol(user, "supervisor"):
        return user["contratista_id"]
    if auth.tiene_rol(user, "supervisor"):
        if not pedido:
            raise ApiError(422, "contratista", "Elegí el contratista")
        return uuid_ok(pedido)
    if auth.tiene_rol(user, "elaborador") and user.get("contratista_id"):
        return user["contratista_id"]
    raise ApiError(403, "sin_contratista", "Tu usuario no tiene un contratista asignado")


def _control_cierre(en=None):
    if cierre_pasado(config.CIERRE_RELEVAMIENTO, en):
        raise ApiError(409, "relevamiento_cerrado", f"El relevamiento de hoy cerró a las {config.CIERRE_RELEVAMIENTO} hs")


@router.post("/pilas")
def guardar_pila(d: Pila, user=Depends(auth.requiere("elaborador", "supervisor"))):
    """Crea o actualiza una pila (id del cliente). Un relevamiento nuevo reemplaza el valor anterior."""
    cn = user["_cn"]
    en = parse_ocurrido(d.ocurrido_en)
    _control_cierre(en)
    cid = _contratista_para(cn, user, d.contratista_id)
    if d.tipo not in ("fino", "grueso") or d.uso not in ("pindo", "ventas"):
        raise ApiError(422, "tipo", "Tipo o uso inválido")
    if d.volumen_m3 <= 0:
        raise ApiError(422, "volumen", "El volumen debe ser mayor que cero")
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_ESPECIES WHERE id = ? AND activo = 1", uuid_ok(d.especie_id)):
        raise ApiError(422, "especie", "Especie inválida")
    if not db.one(cn, "SELECT pies FROM dbo.ZTLOGI_LARGOS WHERE pies = ? AND activo = 1", d.largo_pies):
        raise ApiError(422, "largo", "Largo inválido")
    por = (d.relevado_por or user["nombre"]).strip()[:120] or user["nombre"]
    if d.hora and len(d.hora) == 5 and d.hora[2] == ":":
        try:
            en = en.replace(hour=int(d.hora[:2]), minute=int(d.hora[3:]), second=0)
        except ValueError:
            pass
    vol = redondear1(d.volumen_m3)
    pid = uuid_ok(d.id) if d.id else nuevo_id()
    ex = db.one(cn, "SELECT * FROM dbo.ZTLOGI_PILAS WHERE id = ?", pid)
    if ex:
        if ex["contratista_id"] != cid:
            raise ApiError(403, "pila_ajena", "Esa pila es de otro contratista")
        db.run(cn, "UPDATE dbo.ZTLOGI_PILAS SET especie_id = ?, tipo = ?, largo_pies = ?, volumen_m3 = ?, uso = ?, relevado_en = ?, relevado_por = ?, usuario_id = ?, eliminada = 0, updated_at = ? WHERE id = ?",
               d.especie_id, d.tipo, d.largo_pies, vol, d.uso, en, por, user["id"], ahora(), pid)
    else:
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PILAS (id, contratista_id, especie_id, tipo, largo_pies, volumen_m3, uso, relevado_en, relevado_por, usuario_id) VALUES (?,?,?,?,?,?,?,?,?,?)",
               pid, cid, d.especie_id, d.tipo, d.largo_pies, vol, d.uso, en, por, user["id"])
    db.run(cn, "INSERT INTO dbo.ZTLOGI_PILAS_HIST (pila_id, contratista_id, tipo, largo_pies, uso, volumen_m3, accion, relevado_por, en) VALUES (?,?,?,?,?,?,'relevamiento',?,?)",
           pid, cid, d.tipo, d.largo_pies, d.uso, vol, por, en)
    return db.one(cn, "SELECT p.id, p.contratista_id, p.especie_id, e.nombre AS especie, p.tipo, p.largo_pies, p.volumen_m3, p.uso, p.relevado_en, p.relevado_por FROM dbo.ZTLOGI_PILAS p JOIN dbo.ZTLOGI_ESPECIES e ON e.id = p.especie_id WHERE p.id = ?", pid)


@router.delete("/pilas/{pid}")
def borrar_pila(pid: str, ocurrido_en: str | None = None, user=Depends(auth.requiere("elaborador", "supervisor"))):
    cn = user["_cn"]
    en = parse_ocurrido(ocurrido_en)
    _control_cierre(en)
    p = db.one(cn, "SELECT * FROM dbo.ZTLOGI_PILAS WHERE id = ?", uuid_ok(pid))
    if not p:
        return {"ok": True}
    if not auth.tiene_rol(user, "supervisor") and p["contratista_id"] != user.get("contratista_id"):
        raise ApiError(403, "pila_ajena", "Esa pila es de otro contratista")
    db.run(cn, "UPDATE dbo.ZTLOGI_PILAS SET eliminada = 1, updated_at = ? WHERE id = ?", ahora(), p["id"])
    db.run(cn, "INSERT INTO dbo.ZTLOGI_PILAS_HIST (pila_id, contratista_id, tipo, largo_pies, uso, volumen_m3, accion, relevado_por, en) VALUES (?,?,?,?,?,?,'baja',?,?)",
           p["id"], p["contratista_id"], p["tipo"], p["largo_pies"], p["uso"], p["volumen_m3"], user["nombre"], ahora())
    return {"ok": True}


@router.get("/stock/resumen")
def resumen(user=Depends(auth.requiere("supervisor", "jefe"))):
    cn = user["_cn"]
    return reportes.datos_stock(cn)


@router.get("/reportes/stock.pdf")
def pdf_stock(user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    pdf = reportes.pdf_stock(reportes.datos_stock(cn))
    auditar(cn, "reporte", None, "stock_pdf", None, None, user, user["_ip"])
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="Stock-Pindo-{hhmm().replace(":", "")}.pdf"'})
