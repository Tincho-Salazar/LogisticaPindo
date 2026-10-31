"""Reglas de negocio puras (sin I/O). Son la autoridad: el cliente sólo las replica para la experiencia."""
import datetime as dt


class StockInsuficiente(Exception):
    def __init__(self, detalle):
        super().__init__("stock insuficiente")
        self.detalle = detalle


def _clave(tipo, largo):
    return f"{tipo}|{int(largo)}"


def _r1(x):
    return round(float(x) + 1e-9, 1)


def agrupar_lineas(lineas):
    """Suma volúmenes por (tipo, largo). lineas: [{tipo, largo_pies, volumen_m3}]."""
    acc = {}
    for l in lineas:
        k = _clave(l["tipo"], l["largo_pies"])
        acc[k] = _r1(acc.get(k, 0) + float(l["volumen_m3"]))
    return acc


def descontar_stock(pilas, lineas, circuito):
    """Calcula el descuento de pilas al finalizar una carga.

    pilas: [{id, tipo, largo_pies, uso ('pindo'|'ventas'), volumen_m3}] del contratista.
    circuito 'industria': sólo consume pilas de uso 'pindo'.
    circuito 'ventas': consume primero las pilas 'ventas' y después las 'pindo'.
    Devuelve {pila_id: nuevo_volumen}. Lanza StockInsuficiente con el detalle de la primera línea que no alcanza.
    """
    if circuito not in ("industria", "ventas"):
        raise ValueError("circuito")
    necesidad = agrupar_lineas(lineas)
    nuevos = {}
    for clave, pedido in necesidad.items():
        tipo, largo = clave.split("|")
        cand = [p for p in pilas if p["tipo"] == tipo and int(p["largo_pies"]) == int(largo) and float(p["volumen_m3"]) > 0]
        if circuito == "industria":
            cand = [p for p in cand if p["uso"] != "ventas"]
            cand.sort(key=lambda p: p["id"])
        else:
            cand.sort(key=lambda p: (0 if p["uso"] == "ventas" else 1, p["id"]))
        disponible = _r1(sum(float(p["volumen_m3"]) for p in cand))
        if pedido > disponible + 1e-6:
            raise StockInsuficiente({"tipo": tipo, "largo_pies": int(largo), "disponible": disponible, "pedido": pedido})
        resto = pedido
        for p in cand:
            if resto <= 1e-9:
                break
            toma = min(float(p["volumen_m3"]), resto)
            nuevos[p["id"]] = _r1(float(p["volumen_m3"]) - toma)
            p["volumen_m3"] = nuevos[p["id"]]
            resto = _r1(resto - toma)
    return nuevos


def avance_pedido(lineas_pedido, despachado, stock_pila=None):
    """Avance de cumplimiento de un pedido.

    lineas_pedido: [{tipo, largo_pies, volumen_m3}]; despachado: {'tipo|largo': m3} de cargas finalizadas desde pedido.desde.
    El exceso de una línea no compensa a otra. Lo despachado fuera del pedido se informa aparte.
    """
    stock_pila = stock_pila or {}
    restante = dict(despachado)
    filas = []
    for k, ped in agrupar_lineas(lineas_pedido).items():
        tipo, largo = k.split("|")
        env = _r1(restante.pop(k, 0))
        filas.append({
            "tipo": tipo, "largo_pies": int(largo), "pedido": ped, "enviado": env,
            "avance_pct": min(100, round(env / ped * 100)) if ped else 0,
            "stock_pila": _r1(stock_pila.get(k, 0)),
        })
    pedido_total = _r1(sum(f["pedido"] for f in filas))
    cumplido = sum(min(f["enviado"], f["pedido"]) for f in filas)
    return {
        "lineas": filas,
        "pedido_total": pedido_total,
        "enviado_total": _r1(sum(f["enviado"] for f in filas)),
        "cumplimiento_pct": round(cumplido / pedido_total * 100) if pedido_total else 0,
        "faltante": _r1(max(0, pedido_total - cumplido)),
        "fuera_de_pedido": _r1(sum(restante.values())),
    }


def importe_remito(tarifa, traccion, toneladas=1.0):
    """Importe de un remito: tarifa por tonelada según tracción * toneladas. None si no hay tarifa."""
    if not tarifa:
        return None
    v = tarifa.get("tarifa_4x2") if traccion == "4x2" else tarifa.get("tarifa_6x4")
    if not v or v <= 0:
        return None
    tn = float(toneladas) if toneladas is not None else 1.0
    if tn <= 0:
        return None
    return int(round(float(v) * tn))


def eta_bascula(fin_en, km_asfalto, km_tierra, vel_asfalto=60.0, vel_tierra=25.0):
    """Calcula minutos estimados de viaje y hora estimada de arribo (ETA) a partir de km de asfalto y tierra."""
    if not fin_en:
        return None, None
    ka = max(0.0, float(km_asfalto or 0))
    kt = max(0.0, float(km_tierra or 0))
    if ka <= 0 and kt <= 0:
        viaje_min = 45
    else:
        viaje_min = max(10, round((ka / vel_asfalto + kt / vel_tierra) * 60))
    if isinstance(fin_en, str):
        fin_dt = dt.datetime.fromisoformat(fin_en)
    else:
        fin_dt = fin_en
    eta_dt = fin_dt + dt.timedelta(minutes=viaje_min)
    return viaje_min, eta_dt.strftime("%Y-%m-%dT%H:%M:%S")


def _m(s):
    h, m = str(s).split(":")
    return int(h) * 60 + int(m)


def demora_inicio(hora_plan, hora_real, tolerancia_min=5):
    """Diferencia entre inicio real y confirmado. Devuelve (diferencia, demora, a_horario)."""
    dif = _m(hora_real) - _m(hora_plan)
    dem = max(0, dif)
    return dif, dem, dem <= tolerancia_min


def ciclo_min(fin_en, retorno_en, maximo=1000):
    """Minutos entre salida cargado y retorno a la fila. None si falta un dato o supera el máximo."""
    if not fin_en or not retorno_en:
        return None
    if isinstance(fin_en, str):
        fin_en = dt.datetime.fromisoformat(fin_en)
    if isinstance(retorno_en, str):
        retorno_en = dt.datetime.fromisoformat(retorno_en)
    m = (retorno_en - fin_en).total_seconds() / 60
    return round(m) if 0 < m < maximo else None


def patente_norm(p):
    return "".join(ch for ch in str(p or "").upper() if ch.isalnum())


def normalizar_rodal(x):
    return "".join(ch for ch in str(x or "").upper() if ch.isalnum())
