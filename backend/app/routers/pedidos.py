"""Pedidos de rollos por contratista (supervisor escribe, elaborador lee el propio)."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth, consultas as q, db
from ..util import ApiError, ahora, auditar, hoy, nuevo_id, redondear1, uuid_ok

router = APIRouter(tags=["pedidos"])


class Linea(BaseModel):
    tipo: str
    largo_pies: int = Field(ge=1, le=99)
    volumen_m3: float = Field(gt=0, le=999999)


class Pedido(BaseModel):
    lineas: list[Linea] = Field(min_length=1, max_length=50)
    nota: str | None = Field(default=None, max_length=300)


@router.get("/pedidos")
def todos(user=Depends(auth.requiere("supervisor", "jefe"))):
    cn = user["_cn"]
    return {c["id"]: p for c in db.rows(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE activo = 1") if (p := q.pedido_con_avance(cn, c["id"]))}


@router.get("/pedidos/{contratista_id}")
def uno(contratista_id: str, user=Depends(auth.requiere("supervisor", "elaborador", "jefe"))):
    cn = user["_cn"]
    cid = q.contratista_propio(cn, user, contratista_id, permitir_jefe_lectura=True) if not auth.tiene_rol(user, "supervisor") else uuid_ok(contratista_id)
    return q.pedido_con_avance(cn, cid)


@router.put("/pedidos/{contratista_id}")
def guardar(contratista_id: str, d: Pedido, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    cid = uuid_ok(contratista_id)
    if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE id = ? AND activo = 1", cid):
        raise ApiError(404, "contratista", "Contratista inexistente")
    for l in d.lineas:
        if l.tipo not in ("fino", "grueso"):
            raise ApiError(422, "tipo", "Tipo inválido")
    antes = q.pedido_con_avance(cn, cid)
    if antes:
        pid = antes["id"]
        db.run(cn, "UPDATE dbo.ZTLOGI_PEDIDOS SET nota = ?, creado_por = ?, usuario_id = ?, actualizado_en = ? WHERE id = ?", (d.nota or "").strip() or None, user["nombre"], user["id"], ahora(), pid)
        db.run(cn, "DELETE FROM dbo.ZTLOGI_PEDIDO_LINEAS WHERE pedido_id = ?", pid)
    else:
        pid = nuevo_id()
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PEDIDOS (id, contratista_id, nota, creado_por, usuario_id, creado_en, actualizado_en, desde) VALUES (?,?,?,?,?,?,?,?)",
               pid, cid, (d.nota or "").strip() or None, user["nombre"], user["id"], ahora(), ahora(), hoy())
    for l in d.lineas:
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PEDIDO_LINEAS (pedido_id, tipo, largo_pies, volumen_m3) VALUES (?,?,?,?)", pid, l.tipo, l.largo_pies, redondear1(l.volumen_m3))
    nuevo = q.pedido_con_avance(cn, cid)
    auditar(cn, "pedido", pid, "guardar", antes and {"lineas": antes["lineas"], "nota": antes["nota"]}, {"lineas": nuevo["lineas"], "nota": nuevo["nota"]}, user, user["_ip"])
    return nuevo


@router.delete("/pedidos/{contratista_id}")
def quitar(contratista_id: str, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    cid = uuid_ok(contratista_id)
    antes = q.pedido_con_avance(cn, cid)
    if antes:
        db.run(cn, "DELETE FROM dbo.ZTLOGI_PEDIDOS WHERE id = ?", antes["id"])
        auditar(cn, "pedido", antes["id"], "quitar", {"lineas": antes["lineas"], "nota": antes["nota"]}, None, user, user["_ip"])
    return {"ok": True}
