"""Datos de ejemplo para desarrollo y demo (sección 16.5). NO usar en producción (se niega si APP_ENV=prod).

Uso:  .venv\\Scripts\\python scripts\\seed_demo.py
Crea usuarios de prueba (contraseña Demo.2026): sup.ana, elab.marcos, elab.lucia, transp.hector, transp.raul, bascula.rosa, jefe.carlos
"""
import datetime as dt
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import auth, config, db  # noqa: E402
from app.util import ahora, hoy, manana, nuevo_id  # noqa: E402

CONTRATISTAS = ["Serv. Forestales el Trébol", "Forestal Rio Claro", "Ri-Wal", "Forestal las Coníferas", "Sartori José Carlos"]
DESTINOS = [("Aserradero propio", "industria"), ("Planta de laminado", "industria"), ("Cliente Litoral", "ventas"), ("Cliente Norte", "ventas"), ("Exportación (puerto)", "ventas")]
RODALES = [("MMA07XC073", 0), ("P1A07XC017", 0), ("PIEDIESEL", 1), ("DOS05XC001", 1), ("CMA06XC0E8", 2), ("K1A07XC008", 3), ("SJA09XC016", 4)]
KM = {"Aserradero propio": (9, 14), "Planta de laminado": (24, 14), "Cliente Litoral": (37, 14), "Cliente Norte": (52, 18), "Exportación (puerto)": (68, 20)}
USUARIOS = [
    ("sup.ana", "Ana Pérez", "Pindó SA", "pindo", "Supervisor", "supervisor,bascula", None),
    ("elab.marcos", "Marcos Duarte", CONTRATISTAS[0], "elaborador", "Capataz", "elaborador", 0),
    ("elab.lucia", "Lucía Fernández", CONTRATISTAS[1], "elaborador", "Capataz", "elaborador", 1),
    ("transp.hector", "Héctor Giménez", "Transp. Giménez", "transporte", "Chofer", "transportista", None),
    ("transp.raul", "Raúl Ortiz", "Ortiz Hnos.", "transporte", "Chofer", "transportista", None),
    ("bascula.rosa", "Rosa Benítez", "Pindó SA", "pindo", "Otro", "bascula", None),
    ("jefe.carlos", "Carlos Villalba", "Pindó SA", "pindo", "Jefe de Área Forestal", "jefe", None),
]
CAMIONES = [("AF 412 KR", "Héctor Giménez", "Transp. Giménez", 28, "6x4"), ("AD 087 MT", "Raúl Ortiz", "Ortiz Hnos.", 30, "4x2"), ("AG 653 LP", "Darío Núñez", "Transp. Núñez", 28, "6x4"),
            ("AC 920 BV", "Sergio Acosta", "Acosta Fletes", 30, "6x4"), ("AE 275 FZ", "Luis Vera", "Vera Transportes", 28, "4x2"), ("AH 118 NC", "Cristian Romero", "Romero Fletes", 32, "6x4"),
            ("AB 330 DJ", "Nicolás Paz", "Paz Transportes", 30, "4x2"), ("AA 701 QW", "Pablo Ledesma", "Ledesma Cargas", 30, "6x4")]
PASS = "Demo.2026"


def main():
    if config.APP_ENV == "prod":
        raise SystemExit("seed_demo no se ejecuta en producción")
    random.seed(7)
    with db.tx() as cn:
        if db.scalar(cn, "SELECT COUNT(*) FROM dbo.ZTLOGI_CAMIONES") > 0:
            raise SystemExit("La base ya tiene datos; seed_demo sólo corre sobre una base vacía")
        ids_c = []
        for n in CONTRATISTAS:
            r = db.one(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE nombre = ?", n)
            cid = r["id"] if r else nuevo_id()
            if not r:
                db.run(cn, "INSERT INTO dbo.ZTLOGI_CONTRATISTAS (id, nombre) VALUES (?,?)", cid, n)
            ids_c.append(cid)
        ids_d = {}
        for n, circ in DESTINOS:
            r = db.one(cn, "SELECT id FROM dbo.ZTLOGI_DESTINOS WHERE nombre = ?", n)
            did = r["id"] if r else nuevo_id()
            if not r:
                db.run(cn, "INSERT INTO dbo.ZTLOGI_DESTINOS (id, nombre, circuito) VALUES (?,?,?)", did, n, circ)
            ids_d[n] = (did, circ)
        esp = {e["nombre"]: e["id"] for e in db.rows(cn, "SELECT id, nombre FROM dbo.ZTLOGI_ESPECIES")}
        ids_r = {}
        for i, (cod, ci) in enumerate(RODALES):
            rid = nuevo_id()
            db.run(cn, "INSERT INTO dbo.ZTLOGI_RODALES (id, codigo, contratista_id) VALUES (?,?,?)", rid, cod, ids_c[ci])
            ids_r[cod] = (rid, ids_c[ci])
            for n, (did, _) in ids_d.items():
                ka, kt = KM[n][0] + (i % 3) * 2, KM[n][1] + (i % 4)
                t42 = round((ka * 180 + kt * 95 + 1800) / 50) * 50
                db.run(cn, "INSERT INTO dbo.ZTLOGI_TARIFAS (id, rodal_id, destino_id, km_asfalto, km_tierra, tarifa_4x2, tarifa_6x4, vigente_desde) VALUES (?,?,?,?,?,?,?,?)",
                       nuevo_id(), rid, did, ka, kt, t42, round(t42 * 1.05 / 50) * 50, hoy() - dt.timedelta(days=200))
        ids_u = {}
        for usr, nom, emp, tipo, puesto, roles, ci in USUARIOS:
            uid = nuevo_id()
            db.run(cn, "INSERT INTO dbo.ZTLOGI_USUARIOS (id, usuario, nombre, password_hash, empresa, tipo_empresa, puesto, roles, contratista_id, activo, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,1,?,?)",
                   uid, usr, nom, auth.hash_password(PASS), emp, tipo, puesto, roles, ids_c[ci] if ci is not None else None, ahora(), ahora())
            ids_u[nom] = uid
        ids_k = []
        for i, (pat, cho, emp, cap, tr) in enumerate(CAMIONES):
            kid = nuevo_id()
            pend = i == 7
            db.run(cn, "INSERT INTO dbo.ZTLOGI_CAMIONES (id, patente, patente_norm, chofer, telefono, empresa, capacidad_tn, traccion, estado, alta_estado, alta_en, alta_por, propietario_usuario_id) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                   kid, pat, pat.replace(" ", ""), cho, None, emp, cap, tr, "disponible", "pendiente" if pend else "aprobada", ahora() - dt.timedelta(hours=1), cho, ids_u.get(cho))
            ids_k.append(kid)
        now = ahora()
        rel = now.replace(hour=19, minute=10)
        pilas = [(0, "Pino Taeda", "grueso", 10, 142.5, "pindo", "Marcos Duarte"), (0, "Pino Taeda", "fino", 8, 96.0, "pindo", "Marcos Duarte"), (1, "Pino Híbrido", "grueso", 12, 188.0, "pindo", "Lucía Fernández"),
                 (1, "Pino Híbrido", "fino", 10, 64.5, "pindo", "Lucía Fernández"), (2, "Eucaliptus", "grueso", 20, 210.0, "pindo", "Marcos Duarte"), (3, "Araucaria", "fino", 8, 71.0, "pindo", "Marcos Duarte"),
                 (2, "Eucaliptus", "grueso", 14, 54.0, "ventas", "Marcos Duarte")]
        for ci, e, tipo, largo, m3, uso, por in pilas:
            db.run(cn, "INSERT INTO dbo.ZTLOGI_PILAS (id, contratista_id, especie_id, tipo, largo_pies, volumen_m3, uso, relevado_en, relevado_por) VALUES (?,?,?,?,?,?,?,?,?)",
                   nuevo_id(), ids_c[ci], esp[e], tipo, largo, m3, uso, rel - dt.timedelta(days=1), por)
        # programa hoy y mañana
        for ci, k, h in [(0, 0, "10:00"), (1, 1, "10:30"), (2, 4, "11:00"), (3, 3, "13:00"), (4, 5, "14:00")]:
            db.run(cn, "INSERT INTO dbo.ZTLOGI_PROGRAMA (id, jornada, camion_id, contratista_id, hora, estado) VALUES (?,?,?,?,?,'programado')", nuevo_id(), hoy(), ids_k[k], ids_c[ci], h)
        for ci, k, h in [(0, 0, "06:00"), (1, 1, "06:30"), (2, 4, "07:00"), (3, 3, "07:30")]:
            db.run(cn, "INSERT INTO dbo.ZTLOGI_PROGRAMA (id, jornada, camion_id, contratista_id, hora, estado) VALUES (?,?,?,?,?,'programado')", nuevo_id(), manana(), ids_k[k], ids_c[ci], h)
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PROGRAMA_EMISIONES (jornada, emitido_en) VALUES (?,?)", hoy(), now - dt.timedelta(days=1))
        db.run(cn, "INSERT INTO dbo.ZTLOGI_DISPONIBILIDAD (camion_id, jornada, valor, respondida_en) VALUES (?,?,?,?)", ids_k[0], manana(), "si", now)
        db.run(cn, "INSERT INTO dbo.ZTLOGI_DISPONIBILIDAD (camion_id, jornada, valor, respondida_en) VALUES (?,?,?,?)", ids_k[4], manana(), "no", now)
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PRIORIDAD_FRENTE (jornada, contratista_id, prioridad, en) VALUES (?,?,?,?)", manana(), ids_c[1], "pindo", now)
        db.run(cn, "INSERT INTO dbo.ZTLOGI_SOLICITUDES_UNIDADES (jornada, contratista_id, cantidad_minima, nota, solicitada_por, solicitada_en) VALUES (?,?,?,?,?,?)", manana(), ids_c[1], 3, None, "Lucía Fernández", now)
        pid = nuevo_id()
        db.run(cn, "INSERT INTO dbo.ZTLOGI_PEDIDOS (id, contratista_id, nota, creado_por, creado_en, actualizado_en, desde) VALUES (?,?,?,?,?,?,?)", pid, ids_c[1], "Priorizar largos de 12 pies", "Ana Pérez", now, now, hoy() - dt.timedelta(days=3))
        for tipo, largo, m3 in [("grueso", 12, 60), ("fino", 10, 30), ("grueso", 20, 40)]:
            db.run(cn, "INSERT INTO dbo.ZTLOGI_PEDIDO_LINEAS (pedido_id, tipo, largo_pies, volumen_m3) VALUES (?,?,?,?)", pid, tipo, largo, m3)
        for d, h in [("06:00", "13:00"), ("14:00", "22:00")]:
            db.run(cn, "INSERT INTO dbo.ZTLOGI_BASCULA_TURNOS (id, desde, hasta) VALUES (?,?,?)", nuevo_id(), d, h)
        for d, h, m in [("10:00", "10:30", "Pausa"), ("13:00", "14:00", "Almuerzo")]:
            db.run(cn, "INSERT INTO dbo.ZTLOGI_BASCULA_DESCANSOS (id, desde, hasta, motivo) VALUES (?,?,?,?)", nuevo_id(), d, h, m)
        # histórico de cargas de los últimos 6 días (ciclos, tiempos, báscula) e inicios
        dests = list(ids_d.items())
        rod_de = {ci: [r for r, (rid, c) in ids_r.items() if c == ids_c[ci]] for ci in range(5)}
        for o in range(1, 7):
            dia = hoy() - dt.timedelta(days=o)
            for ci in range(5):
                plan = 7 * 60 + ci * 15
                real = plan + max(0, random.randint(-5, 30))
                db.run(cn, "INSERT INTO dbo.ZTLOGI_INICIOS_DIA (jornada, contratista_id, hora_plan, hora_real, fuente) VALUES (?,?,?,?,'elaborador')", dia, ids_c[ci], f"{plan // 60:02d}:{plan % 60:02d}", f"{real // 60:02d}:{real % 60:02d}")
            for k in range(7):
                for j in range(2):
                    ci = random.randrange(5)
                    dn, (did, circ) = dests[random.randrange(len(dests))]
                    ini = dt.datetime.combine(dia, dt.time(7 + j * 4 + random.randint(0, 2), random.randint(0, 59)))
                    tcarga = 25 + random.randint(0, 30)
                    fin = ini + dt.timedelta(minutes=tcarga)
                    ciclo = 120 + ci * 12 + random.randint(0, 60) + (40 if circ == "ventas" else 0)
                    kid = nuevo_id()
                    db.run(cn, "INSERT INTO dbo.ZTLOGI_CARGAS (id, camion_id, contratista_id, rodal_id, circuito, destino_id, estado, jornada, espera_min, inicio_en, fin_en, retorno_en, operador_nombre) VALUES (?,?,?,?,?,?,'finalizada',?,?,?,?,?,?)",
                           kid, ids_k[k], ids_c[ci], ids_r[rod_de[ci][0]][0], circ, did, dia, random.randint(5, 40), ini, fin, fin + dt.timedelta(minutes=ciclo), "Demo")
                    db.run(cn, "INSERT INTO dbo.ZTLOGI_CARGA_LINEAS (carga_id, tipo, largo_pies, volumen_m3) VALUES (?,?,?,?)", kid, random.choice(["fino", "grueso"]), random.choice([8, 10, 12]), 20 + random.randint(0, 9))
                    if circ == "industria":
                        ing = fin + dt.timedelta(minutes=40 + random.randint(0, 30))
                        db.run(cn, "INSERT INTO dbo.ZTLOGI_BASCULA_MOV (id, carga_id, camion_id, jornada, ingreso_en, salida_en) VALUES (?,?,?,?,?,?)", nuevo_id(), kid, ids_k[k], dia, ing, ing + dt.timedelta(minutes=14 + random.randint(0, 25)))
        # remitos del camión 1 (Héctor)
        rem = [(1, "PIEDIESEL", "Aserradero propio", 27.4), (2, "P1A07XC017", "Cliente Litoral", 28.1), (4, "PIEDIESEL", "Planta de laminado", 26.8), (6, "DOS05XC001", "Cliente Norte", 27.9), (9, "MMA07XC073", "Aserradero propio", 28.4),
               (11, "CMA06XC0E8", "Cliente Litoral", 26.2), (13, "PIEDIESEL", "Aserradero propio", 27.7), (16, "K1A07XC008", "Cliente Norte", 28.0), (19, "SJA09XC016", "Planta de laminado", 27.1), (23, "P1A07XC017", "Aserradero propio", 26.9),
               (27, "DOS05XC001", "Exportación (puerto)", 28.2), (33, "MMA07XC073", "Cliente Litoral", 27.5), (41, "PIEDIESEL", "Cliente Norte", 27.3), (52, "CMA06XC0E8", "Aserradero propio", 28.3)]
        for n, (off, rod, des, tn) in enumerate(rem):
            fecha = hoy() - dt.timedelta(days=off)
            t = db.one(cn, "SELECT id, tarifa_6x4 FROM dbo.ZTLOGI_TARIFAS WHERE rodal_id = ? AND destino_id = ?", ids_r[rod][0], ids_d[des][0])
            imp = int(round(float(t["tarifa_6x4"]) * float(tn)))
            k_match = db.one(cn, "SELECT TOP 1 k.id FROM dbo.ZTLOGI_CARGAS k LEFT JOIN dbo.ZTLOGI_REMITOS r ON r.carga_id = k.id WHERE k.camion_id = ? AND k.jornada = ? AND r.id IS NULL", ids_k[0], fecha)
            db.run(cn, "INSERT INTO dbo.ZTLOGI_REMITOS (id, camion_id, carga_id, numero, fecha, rodal_id, destino_id, toneladas, origen_dato, tarifa_id, tarifa_aplicada, importe, cargado_por, cargado_en) VALUES (?,?,?,?,?,?,?,?,'manual',?,?,?,?,?)",
                   nuevo_id(), ids_k[0], k_match["id"] if k_match else None, f"0001-{45900 - n * 63 - off}", fecha, ids_r[rod][0], ids_d[des][0], tn, t["id"], t["tarifa_6x4"], imp, "Héctor Giménez", dt.datetime.combine(fecha, dt.time(10 + n % 8, 10 + n * 3 % 50)))
    print("Datos de ejemplo cargados. Usuarios (contraseña Demo.2026):", ", ".join(u[0] for u in USUARIOS))


if __name__ == "__main__":
    main()
