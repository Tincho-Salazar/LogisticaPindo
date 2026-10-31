"""Análisis de rendimiento (supervisor): ciclos, tiempos de carga y demoras de inicio, agregados en el servidor."""
import datetime as dt

from fastapi import APIRouter, Depends

from .. import auth, config, db, reglas
from ..util import hoy

router = APIRouter(tags=["analisis"])


def _rank(data, key, val="min", esp="espera_min"):
    grupos = {}
    for c in data:
        k = key(c)
        if k:
            grupos.setdefault(k, []).append(c)
    out = []
    for k, rs in grupos.items():
        vals = [r[val] for r in rs]
        es = [r[esp] for r in rs if r.get(esp) is not None]
        out.append({"key": k, "n": len(rs), "camiones": len({r["camion_id"] for r in rs}), "prom": sum(vals) / len(vals), "min": min(vals), "max": max(vals),
                    "esp": sum(es) / len(es) if es else None})
    return sorted(out, key=lambda r: r["prom"])


@router.get("/analisis")
def analisis(circuito: str = "todos", dias: int = 30, user=Depends(auth.requiere("supervisor"))):
    cn = user["_cn"]
    dias = max(1, min(dias, 180))
    desde = hoy() - dt.timedelta(days=dias)
    cam = {c["id"]: c for c in db.rows(cn, "SELECT id, patente, chofer FROM dbo.ZTLOGI_CAMIONES")}
    contr = {c["id"]: c["nombre"] for c in db.rows(cn, "SELECT id, nombre FROM dbo.ZTLOGI_CONTRATISTAS")}
    dest = {d["id"]: d for d in db.rows(cn, "SELECT id, nombre, circuito FROM dbo.ZTLOGI_DESTINOS")}
    cargas = db.rows(cn, "SELECT id, camion_id, contratista_id, destino_id, circuito, jornada, inicio_en, fin_en, retorno_en, espera_min FROM dbo.ZTLOGI_CARGAS "
                         "WHERE estado = 'finalizada' AND jornada >= ? AND fin_en IS NOT NULL", desde)
    if circuito in ("industria", "ventas"):
        cargas = [k for k in cargas if k["circuito"] == circuito]
    ciclos, tcarga = [], []
    for k in cargas:
        m = reglas.ciclo_min(k["fin_en"], k["retorno_en"])
        if m:
            ciclos.append({**k, "min": m})
        t = (dt.datetime.fromisoformat(k["fin_en"]) - dt.datetime.fromisoformat(k["inicio_en"])).total_seconds() / 60
        if 0 <= t < 300:
            tcarga.append({**k, "min": round(t)})
    nombre_c = lambda r: {**r, "nombre": contr.get(r["key"], "?")}
    nombre_d = lambda r: {**r, "nombre": dest.get(r["key"], {}).get("nombre", "?"), "circuito": dest.get(r["key"], {}).get("circuito")}
    nombre_k = lambda r: {**r, "patente": cam.get(r["key"], {}).get("patente", "?"), "chofer": cam.get(r["key"], {}).get("chofer", "")}
    out = {"circuito": circuito, "dias": dias, "n_ciclos": len(ciclos), "gen_ciclo": (sum(c["min"] for c in ciclos) / len(ciclos)) if ciclos else None}
    esp = [c["espera_min"] for c in ciclos if c["espera_min"] is not None]
    out["espera_prom"] = sum(esp) / len(esp) if esp else None
    out["por_punto"] = [nombre_c(r) for r in _rank(ciclos, lambda c: c["contratista_id"])]
    out["por_destino"] = [nombre_d(r) for r in _rank(ciclos, lambda c: c["destino_id"])]
    out["por_circuito"] = {ci: (sum(c["min"] for c in cs) / len(cs) if cs else None) for ci in ("industria", "ventas") for cs in [[c for c in ciclos if c["circuito"] == ci]]}
    out["por_camion"] = [nombre_k(r) for r in _rank(ciclos, lambda c: c["camion_id"])]
    celdas = {}
    for c in ciclos:
        celdas.setdefault(f"{c['contratista_id']}|{c['destino_id']}", []).append(c["min"])
    out["cruce"] = {"contratistas": [{"id": i, "nombre": n} for i, n in sorted(contr.items(), key=lambda kv: kv[1]) if any(c["contratista_id"] == i for c in ciclos)],
                    "destinos": [{"id": i, "nombre": d["nombre"]} for i, d in dest.items() if any(c["destino_id"] == i for c in ciclos)],
                    "celdas": {k: sum(v) / len(v) for k, v in celdas.items()}}
    ge = [c["espera_min"] for c in tcarga if c["espera_min"] is not None]
    hoy_t = [c for c in tcarga if c["jornada"] == hoy().isoformat()]
    out["tcarga"] = {"n": len(tcarga), "gen": (sum(c["min"] for c in tcarga) / len(tcarga)) if tcarga else None, "espera_prom": sum(ge) / len(ge) if ge else None,
                     "por_camion": [nombre_k(r) for r in _rank(tcarga, lambda c: c["camion_id"])], "por_punto": [nombre_c(r) for r in _rank(tcarga, lambda c: c["contratista_id"])],
                     "hoy": [{"camion_id": c["camion_id"], "patente": cam.get(c["camion_id"], {}).get("patente"), "chofer": cam.get(c["camion_id"], {}).get("chofer"),
                              "contratista": contr.get(c["contratista_id"]), "ini": c["inicio_en"][11:16], "fin": c["fin_en"][11:16], "min": c["min"]} for c in hoy_t]}
    ini = db.rows(cn, "SELECT jornada, contratista_id, hora_plan, hora_real, fuente FROM dbo.ZTLOGI_INICIOS_DIA WHERE jornada >= ?", desde)
    tol = config.TOLERANCIA_DEMORA_MIN
    dem = []
    for x in ini:
        dif, d, ok = reglas.demora_inicio(x["hora_plan"], x["hora_real"], tol)
        dem.append({**x, "contratista": contr.get(x["contratista_id"], "?"), "dif": dif, "dem": d, "a_horario": ok})
    rank = []
    for cid, nombre in contr.items():
        rs = [x for x in dem if x["contratista_id"] == cid]
        if rs:
            rank.append({"key": cid, "nombre": nombre, "n": len(rs), "prom": sum(x["dem"] for x in rs) / len(rs), "max": max(x["dem"] for x in rs), "pt": round(sum(1 for x in rs if x["a_horario"]) / len(rs) * 100)})
    rank.sort(key=lambda r: -r["prom"])
    out["demoras"] = {"tolerancia": tol, "n": len(dem), "gen": (sum(x["dem"] for x in dem) / len(dem)) if dem else None, "pct_horario": round(sum(1 for x in dem if x["a_horario"]) / len(dem) * 100) if dem else None,
                      "hoy": [x for x in dem if x["jornada"] == hoy().isoformat()], "rank": rank}
    return out
