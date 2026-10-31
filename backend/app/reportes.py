"""Datos y PDF de los reportes (ReportLab, A4 vertical, Helvetica, pie 'Página N de M')."""
import datetime as dt
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from . import db
from .util import ahora, hoy

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def f1(x):
    s = f"{float(x or 0):,.1f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def money(x):
    return "$ " + f"{int(round(x or 0)):,}".replace(",", ".")


def fecha_larga(d=None):
    d = d or ahora()
    return d.strftime("%d/%m/%Y %H:%M")


# ---------- datos ----------

def datos_stock(cn):
    pilas = db.rows(cn, "SELECT p.contratista_id, c.nombre AS contratista, p.tipo, p.largo_pies, p.uso, p.volumen_m3, p.relevado_en, p.relevado_por "
                        "FROM dbo.ZTLOGI_PILAS p JOIN dbo.ZTLOGI_CONTRATISTAS c ON c.id = p.contratista_id WHERE p.eliminada = 0 AND p.volumen_m3 > 0")
    largos = [r["pies"] for r in db.rows(cn, "SELECT pies FROM dbo.ZTLOGI_LARGOS WHERE activo = 1 ORDER BY pies")]
    for p in pilas:
        if p["largo_pies"] not in largos:
            largos.append(p["largo_pies"])
    largos.sort()
    contrs = db.rows(cn, "SELECT id, nombre FROM dbo.ZTLOGI_CONTRATISTAS WHERE activo = 1 ORDER BY nombre")

    def fila(ps, l):
        q = [p for p in ps if p["largo_pies"] == l]
        f = sum(p["volumen_m3"] for p in q if p["tipo"] == "fino")
        g = sum(p["volumen_m3"] for p in q if p["tipo"] == "grueso")
        v = sum(p["volumen_m3"] for p in q if p["uso"] == "ventas")
        return {"largo": l, "fino": f, "grueso": g, "total": f + g, "ventas": v, "pindo": f + g - v}

    gen = [fila(pilas, l) for l in largos]
    out_c = []
    for c in contrs:
        ps = [p for p in pilas if p["contratista_id"] == c["id"]]
        rows = [r for r in (fila(ps, l) for l in largos) if r["total"] > 0]
        tot = sum(p["volumen_m3"] for p in ps)
        ven = sum(p["volumen_m3"] for p in ps if p["uso"] == "ventas")
        last = max(ps, key=lambda p: p["relevado_en"]) if ps else None
        out_c.append({"contratista_id": c["id"], "nombre": c["nombre"], "filas": rows, "total": tot, "ventas": ven, "pindo": tot - ven,
                      "ultimo": {"relevado_en": last["relevado_en"], "relevado_por": last["relevado_por"]} if last else None})
    return {"generado": ahora().strftime("%Y-%m-%dT%H:%M:%S"), "total": sum(r["total"] for r in gen), "general": gen, "contratistas": out_c}


def datos_fletes(cn, camion):
    rs = db.rows(cn, "SELECT r.id, r.numero, r.fecha, ro.codigo AS rodal, c.nombre AS contratista, d.nombre AS destino, r.toneladas, r.importe, r.cargado_en "
                     "FROM dbo.ZTLOGI_REMITOS r JOIN dbo.ZTLOGI_RODALES ro ON ro.id = r.rodal_id JOIN dbo.ZTLOGI_CONTRATISTAS c ON c.id = ro.contratista_id "
                     "LEFT JOIN dbo.ZTLOGI_DESTINOS d ON d.id = r.destino_id WHERE r.camion_id = ? AND r.eliminado = 0 ORDER BY r.fecha, r.cargado_en", camion["id"])
    mes_k = hoy().strftime("%Y-%m")
    mes = [r for r in rs if r["fecha"][:7] == mes_k]

    def por_rodal(lista):
        by = {}
        for r in lista:
            b = by.setdefault(r["rodal"], {"rodal": r["rodal"], "contratista": r["contratista"], "remitos": 0, "toneladas": 0.0, "importe": 0})
            b["remitos"] += 1
            b["toneladas"] += r["toneladas"]
            b["importe"] += r["importe"] or 0
        return [by[k] for k in sorted(by)]

    meses, acum = {}, 0
    for r in rs:
        k = r["fecha"][:7]
        b = meses.setdefault(k, {"mes": k, "remitos": 0, "toneladas": 0.0, "importe": 0})
        b["remitos"] += 1
        b["toneladas"] += r["toneladas"]
        b["importe"] += r["importe"] or 0
    lista_meses = []
    for k in sorted(meses):
        acum += meses[k]["importe"]
        meses[k]["acumulado"] = acum
        lista_meses.append(meses[k])
    # serie de 6 meses para el seguimiento (incluye meses sin remitos)
    serie = []
    y, m = hoy().year, hoy().month
    for i in range(5, -1, -1):
        mm_ = m - i
        yy = y + (mm_ - 1) // 12
        mm_ = (mm_ - 1) % 12 + 1
        k = f"{yy:04d}-{mm_:02d}"
        serie.append(meses.get(k, {"mes": k, "remitos": 0, "toneladas": 0.0, "importe": 0}))
    for i, s in enumerate(serie):
        prev = serie[i - 1]["importe"] if i else 0
        s["variacion_pct"] = round((s["importe"] - prev) / prev * 100) if prev and s["mes"] != mes_k else None
    return {
        "camion": {k: camion[k] for k in ("id", "patente", "chofer", "empresa", "traccion")},
        "generado": ahora().strftime("%Y-%m-%dT%H:%M:%S"),
        "mes": {"remitos": len(mes), "toneladas": sum(r["toneladas"] for r in mes), "importe": sum(r["importe"] or 0 for r in mes), "por_rodal": por_rodal(mes), "sin_tarifa": sum(1 for r in mes if not r["importe"])},
        "total": {"remitos": len(rs), "toneladas": sum(r["toneladas"] for r in rs), "importe": sum(r["importe"] or 0 for r in rs), "por_rodal": por_rodal(rs), "sin_tarifa": sum(1 for r in rs if not r["importe"])},
        "meses": lista_meses, "serie": serie,
    }


# ---------- PDF ----------

class _Canvas(canvas.Canvas):
    """Pie de página 'Página N de M' en dos pasadas."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._paginas = []

    def showPage(self):
        self._paginas.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        n = len(self._paginas)
        for st in self._paginas:
            self.__dict__.update(st)
            self.setFont("Helvetica", 8)
            self.drawString(15 * mm, 10 * mm, "Logística Forestal Pindó SA")
            self.drawRightString(A4[0] - 15 * mm, 10 * mm, f"Página {self._pageNumber} de {n}")
            super().showPage()
        super().save()


H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=12, leading=15, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=12)
PS = ParagraphStyle("ps", fontName="Helvetica", fontSize=8.5, leading=11, textColor=colors.HexColor("#555555"))


def _tabla(cols, filas, total=None, anchos=None):
    data = [cols] + filas + ([total] if total else [])
    t = Table(data, colWidths=anchos, repeatRows=1)
    st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8.5), ("FONT", (0, 1), (-1, -1), "Helvetica", 9),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EBEBEB")), ("LINEBELOW", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
          ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if total:
        st.append(("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 9))
    t.setStyle(TableStyle(st))
    return t


def _doc(buf):
    return SimpleDocTemplate(buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=15 * mm, bottomMargin=18 * mm, title="Logística Forestal Pindó SA")


def pdf_stock(D):
    buf = io.BytesIO()
    el = [Paragraph("Logística Forestal Pindó SA", H1), Paragraph("Resumen de stock en pila", P),
          Paragraph(f"Generado: {fecha_larga()} · Total pendiente: {f1(D['total'])} m³", PS), Spacer(1, 8), Paragraph("Stock general por largo (m³)", H2)]
    n1 = lambda v: f1(v) if v > 0 else "-"
    filas = [[f"{r['largo']} pies", n1(r["fino"]), n1(r["grueso"]), n1(r["total"]), n1(r["pindo"]), n1(r["ventas"])] for r in D["general"]]
    G = lambda k: f1(sum(r[k] for r in D["general"]))
    el.append(_tabla(["Largo", "Fino", "Grueso", "Total", "Stock Pindó SA", "Stock ventas"], filas, ["Total", G("fino"), G("grueso"), G("total"), G("pindo"), G("ventas")]))
    el.append(Paragraph("Stock por contratista (m³)", H2))
    for c in D["contratistas"]:
        el.append(Paragraph(f"<b>{c['nombre']}</b> · {f1(c['total'])} m³", P))
        u = c["ultimo"]
        el.append(Paragraph(f"Último relevamiento: {u['relevado_en'][11:16]} por {u['relevado_por']} · Stock Pindó SA {f1(c['pindo'])} m³ · Stock ventas {f1(c['ventas'])} m³" if u else "Sin relevamiento cargado", PS))
        if c["filas"]:
            el.append(_tabla(["Largo", "Fino", "Grueso", "Total"], [[f"{r['largo']} pies", n1(r["fino"]), n1(r["grueso"]), n1(r["total"])] for r in c["filas"]], anchos=[60 * mm, 35 * mm, 35 * mm, 35 * mm]))
        el.append(Spacer(1, 8))
    _doc(buf).build(el, canvasmaker=_Canvas)
    return buf.getvalue()


def pdf_fletes(D):
    buf = io.BytesIO()
    c = D["camion"]
    el = [Paragraph("Logística Forestal Pindó SA", H1), Paragraph("Reporte de rendimiento y facturación de fletes", P),
          Paragraph(f"Transportista: {c['chofer']} · {c['patente']} · camión {c['traccion']} · {c['empresa']}", PS), Paragraph(f"Generado: {fecha_larga()}", PS),
          Spacer(1, 6), Paragraph("Resumen", H2)]
    el.append(_tabla(["", "Remitos", "Toneladas", "Facturación"],
                     [["Mes en curso", str(D["mes"]["remitos"]), f1(D["mes"]["toneladas"]), money(D["mes"]["importe"])],
                      ["Acumulado general", str(D["total"]["remitos"]), f1(D["total"]["toneladas"]), money(D["total"]["importe"])]]))
    cols = ["Rodal", "Contratista", "Remitos", "Toneladas", "Facturación"]
    fr = lambda a: [[r["rodal"], r["contratista"], str(r["remitos"]), f1(r["toneladas"]), money(r["importe"])] for r in a]
    el.append(Paragraph("Mes en curso por rodal", H2))
    el.append(_tabla(cols, fr(D["mes"]["por_rodal"]), ["Total", "", str(D["mes"]["remitos"]), f1(D["mes"]["toneladas"]), money(D["mes"]["importe"])], anchos=[35 * mm, 60 * mm, 25 * mm, 28 * mm, 32 * mm]))
    el.append(Paragraph("Acumulado general por rodal", H2))
    el.append(_tabla(cols, fr(D["total"]["por_rodal"]), ["Total", "", str(D["total"]["remitos"]), f1(D["total"]["toneladas"]), money(D["total"]["importe"])], anchos=[35 * mm, 60 * mm, 25 * mm, 28 * mm, 32 * mm]))
    el.append(Paragraph("Facturación por mes", H2))
    el.append(_tabla(["Mes", "Remitos", "Toneladas", "Facturación", "Acumulado"],
                     [[f"{MESES[int(m['mes'][5:]) - 1]} {m['mes'][:4]}", str(m["remitos"]), f1(m["toneladas"]), money(m["importe"]), money(m["acumulado"])] for m in D["meses"]]))
    if D["total"]["sin_tarifa"]:
        n = D["total"]["sin_tarifa"]
        el.append(Spacer(1, 8))
        el.append(Paragraph(f"{n} remito{'s' if n != 1 else ''} sin tarifa no suma{'n' if n != 1 else ''} a la facturación.", PS))
    _doc(buf).build(el, canvasmaker=_Canvas)
    return buf.getvalue()
