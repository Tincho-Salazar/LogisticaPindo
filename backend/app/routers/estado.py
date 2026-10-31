"""Instantánea de estado por rol: todo lo que la app necesita para dibujar sus pantallas, ya filtrado por permisos."""
import datetime as dt

from fastapi import APIRouter, Depends

from .. import auth, config, consultas as q, db
from ..util import ApiError, ahora, hoy, manana, uuid_ok
from .bascula import estado_bascula, historico_bascula
from .catalogos import leer_catalogos

router = APIRouter(tags=["estado"])


def _base(cn, user, rol):
    h, m = hoy(), manana()
    return {
        "ahora": ahora().strftime("%Y-%m-%dT%H:%M:%S"), "hoy": h.isoformat(), "manana": m.isoformat(),
        "cierres": {"disponibilidad": config.CIERRE_DISPONIBILIDAD, "relevamiento": config.CIERRE_RELEVAMIENTO},
        "tolerancia_demora": config.TOLERANCIA_DEMORA_MIN, "modo_prueba": config.MODO_PRUEBA, "rol": rol,
        "me": {k: user.get(k) for k in ("id", "usuario", "nombre", "empresa", "tipo_empresa", "puesto", "contratista_id", "contratista")} | {"roles": user["roles_lista"]},
        **leer_catalogos(cn),
        "emitido": {"hoy": q.emision(cn, h), "manana": q.emision(cn, m)},
    }


def _transportista(cn, user, out, camion_id):
    h, m = hoy(), manana()
    solo_lectura = q.es_jefe_puesto(user)
    if solo_lectura:
        if not q.es_jefe(user):
            raise ApiError(403, "sin_permiso", "No tenés permiso")
        cam = db.rows(cn, f"SELECT {q.CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.baja = 0 AND c.alta_estado = 'aprobada' ORDER BY c.patente")
    else:
        cam = q.camiones_propios(cn, user)
    out["solo_lectura"] = solo_lectura
    out["camiones"] = q.decorar_camiones(cn, cam, m)
    out["bascula"] = {"estado": estado_bascula(cn), **_horarios(cn)}
    sel = next((c for c in cam if c["id"] == camion_id), None) if camion_id else None
    out["camion_id"] = sel["id"] if sel else None
    if not sel:
        out.update({"programa": [], "pilas": [], "cargas": [], "remitos": [], "rodales": [], "tarifas": [], "prioridad": {}, "inicio_carga": {}})
        return out
    prog_mio = q.programa(cn, [h, m], camion_ids={sel["id"]})
    contrs = {g["contratista_id"] for g in prog_mio}
    if sel.get("fila_contratista_id"):
        contrs.add(sel["fila_contratista_id"])
    prog_all = [g for g in q.programa(cn, [h, m]) if g["contratista_id"] in contrs and (g["jornada"] == h.isoformat() or out["emitido"]["manana"])]
    out["programa"] = prog_all
    out["pilas"] = [p for p in q.pilas_de(cn) if p["contratista_id"] in contrs]
    out["prioridad"] = {j: {cid: r["prioridad"] for cid, r in v.items()} for j, v in q.por_jornada(cn, "ZTLOGI_PRIORIDAD_FRENTE", [h, m], "prioridad").items()}
    out["inicio_carga"] = q.por_jornada(cn, "ZTLOGI_INICIO_CARGA", [h, m], "hora, marcado_por, marcado_en")
    out["cargas"] = q.cargas_desde(cn, h - dt.timedelta(days=7), camion_id=sel["id"])
    out["remitos"] = remitos_de(cn, sel["id"])
    out["rodales"] = q.rodales(cn)
    out["tarifas"] = q.tarifas_vigentes(cn)
    if not solo_lectura:
        otra = "tarifa_6x4" if sel["traccion"] == "4x2" else "tarifa_4x2"
        for t in out["tarifas"]:
            t[otra] = None  # el transportista sólo ve la columna de su tracción
    out["despachos_mes"] = db.scalar(
        cn, "SELECT COUNT(*) FROM dbo.ZTLOGI_CARGAS WHERE camion_id = ? AND estado = 'finalizada' AND jornada >= ?", sel["id"], h.replace(day=1)
    )
    return out


def remitos_de(cn, camion_id, limite=600):
    rs = db.rows(
        cn,
        f"SELECT TOP {int(limite)} r.id, r.camion_id, r.carga_id, r.numero, r.fecha, r.rodal_id, ro.codigo AS rodal, r.destino_id, d.nombre AS destino, r.toneladas, "
        "r.origen_dato, r.tarifa_aplicada, r.importe, r.cargado_por, r.cargado_en, CASE WHEN r.foto_path IS NULL THEN 0 ELSE 1 END AS foto "
        "FROM dbo.ZTLOGI_REMITOS r JOIN dbo.ZTLOGI_RODALES ro ON ro.id = r.rodal_id LEFT JOIN dbo.ZTLOGI_DESTINOS d ON d.id = r.destino_id "
        "WHERE r.camion_id = ? AND r.eliminado = 0 ORDER BY r.fecha DESC, r.cargado_en DESC",
        camion_id,
    )
    from .remitos import foto_url
    for r in rs:
        r["foto"] = bool(r["foto"])
        if r["foto"]:
            r["foto_url"] = foto_url(r["id"])
            r["foto_mini_url"] = foto_url(r["id"], mini=True)
    return rs


def remitos_recientes_sin_precio(cn, desde):
    """Para el supervisor: control de remitos contra despachos (sin exponer tarifa_aplicada ni importe)."""
    rs = db.rows(
        cn,
        "SELECT TOP 400 r.id, r.camion_id, r.carga_id, r.numero, r.fecha, r.rodal_id, ro.codigo AS rodal, ro.contratista_id, "
        "r.destino_id, d.nombre AS destino, d.circuito, r.toneladas, r.origen_dato, r.cargado_por, r.cargado_en, "
        "CASE WHEN r.foto_path IS NULL THEN 0 ELSE 1 END AS foto "
        "FROM dbo.ZTLOGI_REMITOS r JOIN dbo.ZTLOGI_RODALES ro ON ro.id = r.rodal_id LEFT JOIN dbo.ZTLOGI_DESTINOS d ON d.id = r.destino_id "
        "WHERE r.fecha >= ? AND r.eliminado = 0 ORDER BY r.fecha DESC, r.cargado_en DESC",
        desde,
    )
    from .remitos import foto_url
    for r in rs:
        r["foto"] = bool(r["foto"])
        if r["foto"]:
            r["foto_url"] = foto_url(r["id"])
            r["foto_mini_url"] = foto_url(r["id"], mini=True)
    return rs


def _horarios(cn):
    return {
        "turnos": db.rows(cn, "SELECT id, desde, hasta FROM dbo.ZTLOGI_BASCULA_TURNOS ORDER BY desde"),
        "descansos": db.rows(cn, "SELECT id, desde, hasta, motivo FROM dbo.ZTLOGI_BASCULA_DESCANSOS ORDER BY desde"),
    }


def _elaborador(cn, user, out, contratista_id):
    h, m = hoy(), manana()
    solo_lectura = q.es_jefe_puesto(user)
    cid =q.contratista_propio(cn, user, contratista_id, permitir_jefe_lectura=True) if (contratista_id or not solo_lectura) else None
    out["solo_lectura"] = solo_lectura
    out["contratista_id"] = cid
    if not cid:
        out.update({"programa": [], "pilas": [], "cargas": [], "camiones": [], "rodales": [], "pedido": None, "solicitud": {}, "inicio_carga": {}, "prioridad": {}})
        return out
    out["pilas"] = q.pilas_de(cn, cid)
    prog_el = q.programa(cn, [h, m], contratista_id=cid)
    out["programa"] = [g for g in prog_el if g["jornada"] == h.isoformat() or out["emitido"]["manana"]]
    out["cargas"] = q.cargas_desde(cn, h, contratista_id=cid)
    ids = {g["camion_id"] for g in out["programa"]} | {k["camion_id"] for k in out["cargas"]}
    cam = db.rows(cn, f"SELECT {q.CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.baja = 0 AND (c.fila_contratista_id = ? OR c.id IN (SELECT camion_id FROM dbo.ZTLOGI_PROGRAMA WHERE jornada IN (?,?) AND contratista_id = ?)) ORDER BY c.patente", cid, h, m, cid)
    cam = [c for c in cam if c["id"] in ids or c.get("fila_contratista_id") == cid]
    out["camiones"] = q.decorar_camiones(cn, cam, m)
    out["pedido"] = q.pedido_con_avance(cn, cid, out["pilas"])
    out["solicitud"] = q.por_jornada(cn, "ZTLOGI_SOLICITUDES_UNIDADES", [m], "cantidad_minima, nota, solicitada_por, solicitada_en", cid)
    out["inicio_carga"] = q.por_jornada(cn, "ZTLOGI_INICIO_CARGA", [h, m], "hora, marcado_por, marcado_en", cid)
    out["prioridad"] = {j: {c: r["prioridad"] for c, r in v.items()} for j, v in q.por_jornada(cn, "ZTLOGI_PRIORIDAD_FRENTE", [h, m], "prioridad", cid).items()}
    out["rodales"] = q.rodales(cn, cid)
    out["destinos_todos"] = out["destinos"]
    return out


def _supervisor(cn, user, out):
    h, m = hoy(), manana()
    cam = db.rows(cn, f"SELECT {q.CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.baja = 0 AND c.alta_estado IN ('aprobada','pendiente') ORDER BY c.patente")
    out["camiones"] = q.decorar_camiones(cn, cam, m)
    out["pilas"] = q.pilas_de(cn)
    out["programa"] = q.programa(cn, [h, m])
    desde_traza = h - dt.timedelta(days=7)
    out["cargas"] = q.cargas_desde(cn, desde_traza)
    out["remitos_control"] = remitos_recientes_sin_precio(cn, desde_traza)
    out["rodales_catalogo"] = q.rodales(cn)
    out["prioridad"] = {j: {c: r["prioridad"] for c, r in v.items()} for j, v in q.por_jornada(cn, "ZTLOGI_PRIORIDAD_FRENTE", [h, m], "prioridad").items()}
    out["solicitud"] = q.por_jornada(cn, "ZTLOGI_SOLICITUDES_UNIDADES", [m], "cantidad_minima, nota, solicitada_por, solicitada_en")
    out["inicio_carga"] = q.por_jornada(cn, "ZTLOGI_INICIO_CARGA", [h, m], "hora, marcado_por, marcado_en")
    pilas_por = {}
    for p in out["pilas"]:
        pilas_por.setdefault(p["contratista_id"], []).append(p)
    out["pedidos"] = {}
    for c in out["contratistas"]:
        pd = q.pedido_con_avance(cn, c["id"], pilas_por.get(c["id"], []))
        if pd:
            out["pedidos"][c["id"]] = pd
    out["inicios_dia"] = db.rows(cn, "SELECT jornada, contratista_id, hora_plan, hora_real, fuente FROM dbo.ZTLOGI_INICIOS_DIA WHERE jornada = ?", h)
    return out


def _bascula(cn, user, out):
    h = hoy()
    cam = db.rows(cn, f"SELECT {q.CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.baja = 0 AND c.alta_estado = 'aprobada' ORDER BY c.patente")
    out["camiones"] = q.decorar_camiones(cn, cam, manana())
    out["cargas"] = q.cargas_desde(cn, h, solo_pendientes_bascula=True)
    out["movimientos"] = db.rows(
        cn, "SELECT b.id, b.carga_id, b.camion_id, b.jornada, b.ingreso_en, b.salida_en FROM dbo.ZTLOGI_BASCULA_MOV b WHERE b.jornada = ? OR b.salida_en IS NULL ORDER BY b.ingreso_en", h
    )
    out["bascula"] = {"estado": estado_bascula(cn), **_horarios(cn), "hist": historico_bascula(cn, 30)}
    return out


def _jefe(cn, user, out):
    out["rodales"] = q.rodales(cn)
    out["tarifas"] = q.tarifas_vigentes(cn)
    return out


@router.get("/estado")
def estado(rol: str, camion_id: str | None = None, contratista_id: str | None = None, user=Depends(auth.usuario_actual)):
    cn = user["_cn"]
    roles = user["roles_lista"]
    permitido = rol in roles or (q.es_jefe(user) and rol in ("transportista", "elaborador"))
    if not permitido:
        raise ApiError(403, "rol_no_habilitado", "Ese rol no está habilitado para tu usuario")
    out = _base(cn, user, rol)
    if rol == "transportista":
        return _transportista(cn, user, out, uuid_ok(camion_id) if camion_id else None)
    if rol == "elaborador":
        return _elaborador(cn, user, out, contratista_id)
    if rol == "supervisor":
        return _supervisor(cn, user, out)
    if rol == "bascula":
        return _bascula(cn, user, out)
    if rol == "jefe":
        return _jefe(cn, user, out)
    return out
