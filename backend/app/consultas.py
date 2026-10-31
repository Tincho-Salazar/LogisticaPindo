"""Consultas compartidas entre routers (camiones propios, pilas, tarifas vigentes, avance de pedido)."""
import datetime as dt

from . import db, reglas
from .util import ApiError, hoy, uuid_ok

CAMION_COLS = ("c.id, c.patente, c.chofer, c.telefono, c.empresa, c.capacidad_tn, c.traccion, c.estado, c.alta_estado, c.alta_en, c.alta_por, "
               "c.propietario_usuario_id, c.fila_desde, c.fila_contratista_id, c.baja, c.version")


def es_jefe(user):
    return "jefe" in user["roles_lista"]


def es_jefe_puesto(user):
    """El Jefe de Área Forestal y el administrador entran a los paneles de transporte y cosecha sólo en modo lectura (ven todos los camiones y contratistas)."""
    return user.get("puesto") == "Jefe de Área Forestal" or "admin" in user["roles_lista"]


def camiones_propios(cn, user):
    """Camiones que el usuario dio de alta o donde figura como chofer (no eliminados)."""
    return db.rows(
        cn,
        f"SELECT {CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.baja = 0 AND (c.propietario_usuario_id = ? OR LOWER(c.chofer) = LOWER(?)) ORDER BY c.patente",
        user["id"], user["nombre"],
    )


def camion_propio(cn, user, camion_id, permitir_jefe_lectura=False):
    camion_id = uuid_ok(camion_id)
    c = db.one(cn, f"SELECT {CAMION_COLS} FROM dbo.ZTLOGI_CAMIONES c WHERE c.id = ? AND c.baja = 0", camion_id)
    if not c:
        raise ApiError(404, "camion_inexistente", "Camión inexistente")
    propio = c["propietario_usuario_id"] == user["id"] or (c["chofer"] or "").lower() == (user["nombre"] or "").lower()
    if not propio and not (permitir_jefe_lectura and es_jefe(user)):
        raise ApiError(403, "camion_ajeno", "Ese camión no es tuyo")
    return c


def contratista_propio(cn, user, contratista_id=None, permitir_jefe_lectura=False):
    """Elaborador: su contratista. Jefe en solo lectura: el que pida."""
    if "elaborador" in user["roles_lista"] and user.get("contratista_id") and not (contratista_id and contratista_id != user["contratista_id"]):
        return user["contratista_id"]
    if permitir_jefe_lectura and es_jefe(user) and contratista_id:
        cid = uuid_ok(contratista_id)
        if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE id = ?", cid):
            raise ApiError(404, "contratista_inexistente", "Contratista inexistente")
        return cid
    if "supervisor" in user["roles_lista"] and contratista_id:
        return uuid_ok(contratista_id)
    raise ApiError(403, "sin_contratista", "Tu usuario no tiene un contratista asignado")


def incidencias_abiertas(cn, camion_ids=None):
    rs = db.rows(cn, "SELECT id, camion_id, tipo, motivo, detalle, minutos, desde FROM dbo.ZTLOGI_INCIDENCIAS WHERE resuelta_en IS NULL ORDER BY desde")
    out = {}
    for r in rs:
        if camion_ids is None or r["camion_id"] in camion_ids:
            out[r["camion_id"]] = r
    return out


def disponibilidad(cn, jornada):
    return {r["camion_id"]: r for r in db.rows(cn, "SELECT camion_id, valor, respondida_en FROM dbo.ZTLOGI_DISPONIBILIDAD WHERE jornada = ?", jornada)}


def decorar_camiones(cn, camiones, jornada_manana):
    inc = incidencias_abiertas(cn)
    disp = disponibilidad(cn, jornada_manana)
    for c in camiones:
        i = inc.get(c["id"])
        c["inc"] = {k: i[k] for k in ("id", "tipo", "motivo", "detalle", "minutos", "desde")} if i else None
        d = disp.get(c["id"])
        c["disp_manana"] = {"valor": d["valor"], "respondida_en": d["respondida_en"]} if d else None
    return camiones


def pilas_de(cn, contratista_id=None):
    sql = ("SELECT p.id, p.contratista_id, p.especie_id, e.nombre AS especie, p.tipo, p.largo_pies, p.volumen_m3, p.uso, p.relevado_en, p.relevado_por "
           "FROM dbo.ZTLOGI_PILAS p JOIN dbo.ZTLOGI_ESPECIES e ON e.id = p.especie_id WHERE p.eliminada = 0")
    if contratista_id:
        return db.rows(cn, sql + " AND p.contratista_id = ? ORDER BY p.relevado_en", contratista_id)
    return db.rows(cn, sql + " ORDER BY p.relevado_en")


def cargas_desde(cn, desde, contratista_id=None, camion_id=None, solo_pendientes_bascula=False):
    sql = ("SELECT k.id, k.camion_id, k.contratista_id, k.rodal_id, r.codigo AS rodal, k.programa_id, k.circuito, k.destino_id, d.nombre AS destino, "
           "k.estado, k.jornada, k.fila_desde, k.espera_min, k.inicio_en, k.fin_en, k.retorno_en, k.operador_nombre, "
           "b.ingreso_en, b.salida_en, b.id AS bascula_id, "
           "t.km_asfalto, t.km_tierra, "
           "rm.id AS remito_id, rm.numero AS remito_numero, rm.toneladas AS remito_tn, "
           "CASE WHEN rm.foto_path IS NULL THEN 0 ELSE 1 END AS remito_foto "
           "FROM dbo.ZTLOGI_CARGAS k LEFT JOIN dbo.ZTLOGI_RODALES r ON r.id = k.rodal_id LEFT JOIN dbo.ZTLOGI_DESTINOS d ON d.id = k.destino_id "
           "LEFT JOIN dbo.ZTLOGI_BASCULA_MOV b ON b.carga_id = k.id "
           "LEFT JOIN dbo.ZTLOGI_TARIFAS t ON t.rodal_id = k.rodal_id AND t.destino_id = k.destino_id AND t.vigente_hasta IS NULL "
           "OUTER APPLY (SELECT TOP 1 id, numero, toneladas, foto_path FROM dbo.ZTLOGI_REMITOS WHERE carga_id = k.id AND eliminado = 0 ORDER BY cargado_en DESC) rm "
           "WHERE (k.jornada >= ? OR k.estado = 'en_curso'")
    params = [desde]
    if solo_pendientes_bascula:
        sql += " OR (k.estado = 'finalizada' AND k.circuito = 'industria' AND b.salida_en IS NULL AND k.jornada >= ?)"
        params.append(desde - dt.timedelta(days=5))
    sql += ")"
    if contratista_id:
        sql += " AND k.contratista_id = ?"
        params.append(contratista_id)
    if camion_id:
        sql += " AND k.camion_id = ?"
        params.append(camion_id)
    sql += " ORDER BY k.inicio_en"
    cargas = db.rows(cn, sql, *params)
    if cargas:
        ids = [k["id"] for k in cargas]
        lineas = {}
        for i in range(0, len(ids), 500):
            chunk = ids[i:i + 500]
            marks = ",".join("?" * len(chunk))
            for l in db.rows(cn, f"SELECT carga_id, tipo, largo_pies, volumen_m3 FROM dbo.ZTLOGI_CARGA_LINEAS WHERE carga_id IN ({marks}) ORDER BY id", *chunk):
                lineas.setdefault(l["carga_id"], []).append({"tipo": l["tipo"], "largo_pies": l["largo_pies"], "volumen_m3": l["volumen_m3"]})
        for k in cargas:
            k["lineas"] = lineas.get(k["id"], [])
            k["remito_foto"] = bool(k.get("remito_foto"))
            viaje_min, eta_en = reglas.eta_bascula(k.get("fin_en"), k.get("km_asfalto"), k.get("km_tierra"))
            k["viaje_est_min"] = viaje_min
            k["eta_en"] = eta_en
    return cargas


def tarifa_vigente(cn, rodal_id, destino_id, fecha):
    if not rodal_id or not destino_id:
        return None
    return db.one(
        cn,
        "SELECT TOP 1 id, tarifa_4x2, tarifa_6x4 FROM dbo.ZTLOGI_TARIFAS WHERE rodal_id = ? AND destino_id = ? AND vigente_desde <= ? "
        "AND (vigente_hasta IS NULL OR vigente_hasta >= ?) ORDER BY vigente_desde DESC",
        rodal_id, destino_id, fecha, fecha,
    )


def tarifas_vigentes(cn):
    return db.rows(cn, "SELECT id, rodal_id, destino_id, km_asfalto, km_tierra, tarifa_4x2, tarifa_6x4, vigente_desde FROM dbo.ZTLOGI_TARIFAS WHERE vigente_hasta IS NULL")


def rodales(cn, contratista_id=None):
    sql = "SELECT r.id, r.codigo, r.contratista_id, c.nombre AS contratista FROM dbo.ZTLOGI_RODALES r JOIN dbo.ZTLOGI_CONTRATISTAS c ON c.id = r.contratista_id WHERE r.activo = 1"
    if contratista_id:
        return db.rows(cn, sql + " AND r.contratista_id = ? ORDER BY r.codigo", contratista_id)
    return db.rows(cn, sql + " ORDER BY r.codigo")


def despachado_desde(cn, contratista_id, desde):
    rs = db.rows(
        cn,
        "SELECT l.tipo, l.largo_pies, SUM(l.volumen_m3) AS m3 FROM dbo.ZTLOGI_CARGA_LINEAS l JOIN dbo.ZTLOGI_CARGAS k ON k.id = l.carga_id "
        "WHERE k.contratista_id = ? AND k.estado = 'finalizada' AND k.jornada >= ? GROUP BY l.tipo, l.largo_pies",
        contratista_id, desde,
    )
    return {f"{r['tipo']}|{int(r['largo_pies'])}": float(r["m3"]) for r in rs}


def pedido_con_avance(cn, contratista_id, pilas=None):
    p = db.one(cn, "SELECT id, contratista_id, nota, creado_por, creado_en, actualizado_en, desde FROM dbo.ZTLOGI_PEDIDOS WHERE contratista_id = ?", contratista_id)
    if not p:
        return None
    p["lineas"] = db.rows(cn, "SELECT tipo, largo_pies, volumen_m3 FROM dbo.ZTLOGI_PEDIDO_LINEAS WHERE pedido_id = ? ORDER BY id", p["id"])
    stock = {}
    for q in (pilas if pilas is not None else pilas_de(cn, contratista_id)):
        k = f"{q['tipo']}|{int(q['largo_pies'])}"
        stock[k] = stock.get(k, 0) + float(q["volumen_m3"])
    p["avance"] = reglas.avance_pedido(p["lineas"], despachado_desde(cn, contratista_id, dt.date.fromisoformat(p["desde"])), stock)
    return p


def emision(cn, jornada):
    return db.one(cn, "SELECT TOP 1 emitido_en FROM dbo.ZTLOGI_PROGRAMA_EMISIONES WHERE jornada = ? ORDER BY emitido_en DESC", jornada)


def programa(cn, jornadas, contratista_id=None, camion_ids=None):
    marks = ",".join("?" * len(jornadas))
    sql = f"SELECT id, jornada, camion_id, contratista_id, hora, estado, orden FROM dbo.ZTLOGI_PROGRAMA WHERE jornada IN ({marks}) AND estado IN ('programado','cargando','cumplido')"
    params = list(jornadas)
    if contratista_id:
        sql += " AND contratista_id = ?"
        params.append(contratista_id)
    rs = db.rows(cn, sql + " ORDER BY jornada, hora, orden", *params)
    if camion_ids is not None:
        rs = [g for g in rs if g["camion_id"] in camion_ids]
    return rs


def por_jornada(cn, tabla, jornadas, cols, contratista_id=None):
    marks = ",".join("?" * len(jornadas))
    sql = f"SELECT jornada, contratista_id, {cols} FROM dbo.{tabla} WHERE jornada IN ({marks})"
    params = list(jornadas)
    if contratista_id:
        sql += " AND contratista_id = ?"
        params.append(contratista_id)
    out = {str(j): {} for j in jornadas}
    for r in db.rows(cn, sql, *params):
        out[r["jornada"]][r["contratista_id"]] = r
    return out
