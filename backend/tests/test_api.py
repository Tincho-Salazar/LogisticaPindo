"""Prueba de integración contra la base local con datos demo (scripts/seed_demo.py).

Recorre un día de operación: disponibilidad, fila, inicio y fin de carga con descuento de stock, báscula,
programa, pedido, tarifario, remito, PDF, análisis y controles de permisos. Se salta si no hay base.
"""
import datetime as dt
import os

os.environ.setdefault("LF_ENV", ".env")  # las pruebas usan el entorno local; reset_demo se niega si APP_ENV=prod
os.environ["MODO_PRUEBA"] = "false"  # los permisos se prueban como en producción (load_dotenv no pisa variables ya definidas)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

try:
    from app import db
    with db.tx() as cn:
        _demo = db.scalar(cn, "SELECT COUNT(*) FROM dbo.ZTLOGI_USUARIOS WHERE usuario = 'sup.ana'")
except Exception:  # noqa: BLE001
    _demo = 0
pytestmark = pytest.mark.skipif(not _demo, reason="requiere la base local con seed_demo")

from app.main import app  # noqa: E402

c = TestClient(app, raise_server_exceptions=False)
PASS = "Demo.2026"


@pytest.fixture(scope="module", autouse=True)
def _datos_demo():
    """Deja la base como recién sembrada para que la prueba sea repetible."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
    import reset_demo
    reset_demo.main()


def login(u):
    r = c.post("/api/v1/auth/login", json={"usuario": u, "password": PASS})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}, r.json()


def test_login_y_bloqueo():
    assert c.post("/api/v1/auth/login", json={"usuario": "sup.ana", "password": "mala"}).status_code == 401
    assert c.post("/api/v1/auth/login", json={"usuario": "nadie", "password": "mala"}).status_code == 401
    h, s = login("sup.ana")
    assert "supervisor" in s["usuario"]["roles"]
    r = c.post("/api/v1/auth/refresh", json={"refresh_token": s["refresh_token"]})
    assert r.status_code == 200
    # reutilizar el refresh viejo revoca la familia
    assert c.post("/api/v1/auth/refresh", json={"refresh_token": s["refresh_token"]}).status_code == 401
    assert c.post("/api/v1/auth/refresh", json={"refresh_token": r.json()["refresh_token"]}).status_code == 401


def test_estado_por_rol_y_permisos():
    h, _ = login("sup.ana")
    e = c.get("/api/v1/estado", params={"rol": "supervisor"}, headers=h).json()
    assert len(e["camiones"]) == 8 and len(e["pilas"]) == 7 and e["programa"]
    assert "tarifas" not in e
    assert c.get("/api/v1/rodales", headers=h).status_code == 403  # supervisor sin acceso al tarifario
    assert c.get("/api/v1/estado", params={"rol": "jefe"}, headers=h).status_code == 403
    hj, _ = login("jefe.carlos")
    ej = c.get("/api/v1/estado", params={"rol": "jefe"}, headers=hj).json()
    assert len(ej["rodales"]) == 7 and len(ej["tarifas"]) == 35
    # jefe en solo lectura sobre transporte
    cam = c.get("/api/v1/estado", params={"rol": "transportista"}, headers=hj).json()
    assert cam["solo_lectura"] and len(cam["camiones"]) == 7
    cid = cam["camiones"][0]["id"]
    assert c.post(f"/api/v1/camiones/{cid}/incidencias", json={"tipo": "demora", "motivo": "Clima"}, headers=hj).status_code == 403
    assert c.get("/api/v1/usuarios", headers=hj).status_code == 403


def test_dia_de_operacion():
    ht, st = login("transp.hector")
    et = c.get("/api/v1/estado", params={"rol": "transportista"}, headers=ht).json()
    assert len(et["camiones"]) == 1 and not et["solo_lectura"]
    cam = et["camiones"][0]
    et = c.get("/api/v1/estado", params={"rol": "transportista", "camion_id": cam["id"]}, headers=ht).json()
    assert et["camion_id"] == cam["id"] and len(et["remitos"]) == 14
    assert all(t["tarifa_4x2"] is None for t in et["tarifas"])  # sólo ve su tracción (6x4)
    # disponibilidad para mañana (depende de la hora de cierre)
    r = c.put(f"/api/v1/camiones/{cam['id']}/disponibilidad-manana", json={"valor": "si"}, headers=ht)
    assert r.status_code in (200, 409)
    # otro transportista no puede tocar este camión
    hr, _ = login("transp.raul")
    assert c.post(f"/api/v1/camiones/{cam['id']}/entrar-fila", headers=hr).status_code == 403
    # entrar en fila (tiene programa hoy en el Trébol)
    r = c.post(f"/api/v1/camiones/{cam['id']}/entrar-fila", headers=ht)
    assert r.status_code == 200 and r.json()["estado"] == "fila", r.text
    # elaborador del Trébol inicia la carga
    he, _ = login("elab.marcos")
    ee = c.get("/api/v1/estado", params={"rol": "elaborador"}, headers=he).json()
    g = next(x for x in ee["programa"] if x["camion_id"] == cam["id"] and x["jornada"] == ee["hoy"])
    r = c.post("/api/v1/cargas", json={"programa_item_id": g["id"]}, headers=he)
    assert r.status_code == 201, r.text
    kid = r.json()["id"]
    assert c.post("/api/v1/cargas", json={"id": kid, "programa_item_id": g["id"]}, headers=he).status_code == 201  # idempotente
    # otro elaborador no puede finalizarla
    hl, _ = login("elab.lucia")
    assert c.post(f"/api/v1/cargas/{kid}/finalizar", json={"circuito": "industria", "destino_id": ee["destinos"][0]["id"], "lineas": [{"tipo": "grueso", "largo_pies": 10, "volumen_m3": 1}]}, headers=hl).status_code == 404
    ind = next(d for d in ee["destinos"] if d["circuito"] == "industria")
    ven = next(d for d in ee["destinos"] if d["circuito"] == "ventas")
    rod = ee["rodales"][0]["id"]
    # stock insuficiente -> 409 con detalle
    r = c.post(f"/api/v1/cargas/{kid}/finalizar", json={"circuito": "industria", "rodal_id": rod, "destino_id": ind["id"], "lineas": [{"tipo": "grueso", "largo_pies": 10, "volumen_m3": 999}]}, headers=he)
    assert r.status_code == 409 and r.json()["codigo"] == "stock_insuficiente"
    # destino de otro circuito -> 422
    assert c.post(f"/api/v1/cargas/{kid}/finalizar", json={"circuito": "industria", "rodal_id": rod, "destino_id": ven["id"], "lineas": [{"tipo": "grueso", "largo_pies": 10, "volumen_m3": 1}]}, headers=he).status_code == 422
    r = c.post(f"/api/v1/cargas/{kid}/finalizar", json={"circuito": "industria", "rodal_id": rod, "destino_id": ind["id"], "lineas": [{"tipo": "grueso", "largo_pies": 10, "volumen_m3": 18.6}, {"tipo": "fino", "largo_pies": 8, "volumen_m3": 11.4}]}, headers=he)
    assert r.status_code == 200 and r.json()["total_m3"] == 30.0, r.text
    ee = c.get("/api/v1/estado", params={"rol": "elaborador"}, headers=he).json()
    assert next(p["volumen_m3"] for p in ee["pilas"] if p["tipo"] == "grueso" and p["largo_pies"] == 10) == 123.9
    assert next(k for k in ee["cargas"] if k["id"] == kid)["estado"] == "finalizada"
    # el camión quedó en ruta a industria: no puede avisar descarga
    assert c.post(f"/api/v1/camiones/{cam['id']}/estado", json={"estado": "vacio"}, headers=ht).status_code == 409
    # báscula: ingreso y salida -> disponible
    hb, _ = login("bascula.rosa")
    eb = c.get("/api/v1/estado", params={"rol": "bascula"}, headers=hb).json()
    assert any(k["id"] == kid and k["circuito"] == "industria" for k in eb["cargas"])
    r = c.post("/api/v1/bascula/ingresos", json={"camion_id": cam["id"]}, headers=hb)
    assert r.status_code == 201 and r.json()["carga_id"] == kid
    assert c.post("/api/v1/bascula/ingresos", json={"camion_id": cam["id"]}, headers=hb).status_code == 409
    assert c.post(f"/api/v1/bascula/ingresos/{r.json()['id']}/salida", headers=hb).status_code == 200
    et = c.get("/api/v1/estado", params={"rol": "transportista", "camion_id": cam["id"]}, headers=ht).json()
    assert et["camiones"][0]["estado"] == "disponible"
    eb = c.get("/api/v1/estado", params={"rol": "bascula"}, headers=hb).json()
    assert eb["bascula"]["hist"]["dias_n"] >= 1 and "estado" in eb["bascula"]
    assert "hist" not in et["bascula"]  # el transportista sólo ve horarios y estado


def test_programa_pedido_y_analisis():
    hs, _ = login("sup.ana")
    e = c.get("/api/v1/estado", params={"rol": "supervisor"}, headers=hs).json()
    libre = next(k for k in e["camiones"] if k["alta_estado"] == "aprobada" and not any(g["camion_id"] == k["id"] and g["jornada"] == e["manana"] and g["estado"] == "programado" for g in e["programa"]) and (k["disp_manana"] or {}).get("valor") != "no")
    contr = e["contratistas"][0]["id"]
    r = c.post("/api/v1/programa/manana/items", json={"items": [{"camion_id": libre["id"], "contratista_id": contr, "hora": "08:15"}]}, headers=hs)
    assert r.status_code == 201, r.text
    gid = r.json()["ids"][0]
    assert c.post("/api/v1/programa/manana/items", json={"items": [{"camion_id": libre["id"], "contratista_id": contr, "hora": "09:00"}]}, headers=hs).status_code == 409
    assert c.delete(f"/api/v1/programa/items/{gid}", headers=hs).status_code == 200
    assert c.post("/api/v1/programa/manana/emitir", headers=hs).status_code == 200
    assert c.put(f"/api/v1/programa/manana/prioridad/{contr}", json={"prioridad": "ventas"}, headers=hs).status_code == 200
    sin_stock = next(x["id"] for x in e["contratistas"] if not any(p["contratista_id"] == x["id"] for p in e["pilas"]))
    assert c.put(f"/api/v1/programa/manana/prioridad/{sin_stock}", json={"prioridad": "pindo"}, headers=hs).status_code == 409
    # altas pendientes
    pend = next(k for k in e["camiones"] if k["alta_estado"] == "pendiente")
    assert c.post(f"/api/v1/camiones/{pend['id']}/aprobar", headers=hs).json()["alta_estado"] == "aprobada"
    # pedido y avance
    r = c.put(f"/api/v1/pedidos/{contr}", json={"lineas": [{"tipo": "grueso", "largo_pies": 10, "volumen_m3": 60}, {"tipo": "fino", "largo_pies": 8, "volumen_m3": 30}], "nota": "probar"}, headers=hs)
    assert r.status_code == 200 and r.json()["avance"]["pedido_total"] == 90.0
    he, _ = login("elab.marcos")
    assert c.put(f"/api/v1/pedidos/{contr}", json={"lineas": [{"tipo": "grueso", "largo_pies": 10, "volumen_m3": 1}]}, headers=he).status_code == 403
    assert c.put("/api/v1/programa/manana/solicitud", json={"cantidad_minima": 4, "nota": "largos"}, headers=he).status_code == 200
    assert c.put("/api/v1/programa/manana/inicio", json={"hora": "07:15"}, headers=he).status_code == 200
    assert c.put("/api/v1/programa/manana/inicio", json={"hora": "7:15"}, headers=he).status_code == 422
    a = c.get("/api/v1/analisis", params={"circuito": "todos"}, headers=hs).json()
    assert a["n_ciclos"] > 50 and a["por_punto"] and a["demoras"]["rank"]
    assert c.get("/api/v1/analisis", headers=he).status_code == 403
    r = c.get("/api/v1/reportes/stock.pdf", headers=hs)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"


def test_tarifario_y_remitos():
    hj, _ = login("jefe.carlos")
    e = c.get("/api/v1/estado", params={"rol": "jefe"}, headers=hj).json()
    r = c.post("/api/v1/rodales", json={"codigo": "test rodal 1", "contratista_id": e["contratistas"][0]["id"]}, headers=hj)
    assert r.status_code == 201 and r.json()["codigo"] == "TESTRODAL1"
    rid = r.json()["id"]
    assert c.post("/api/v1/rodales", json={"codigo": "TESTRODAL1", "contratista_id": e["contratistas"][0]["id"]}, headers=hj).status_code == 409
    did = e["destinos"][0]["id"]
    r = c.put(f"/api/v1/rodales/{rid}/tarifas/{did}", json={"km_asfalto": 10, "km_tierra": 5, "tarifa_4x2": 5500, "tarifa_6x4": 5800}, headers=hj)
    assert r.status_code == 200
    r = c.put(f"/api/v1/rodales/{rid}/tarifas/{did}", json={"km_asfalto": 10, "km_tierra": 5, "tarifa_4x2": 6000, "tarifa_6x4": 6300}, headers=hj)
    assert r.status_code == 200 and r.json()["tarifa_4x2"] == 6000
    csv = "Empresa;Rodal;Destino;Km asfalto;Km tierra;4x2;6x4\n" + f"{e['contratistas'][1]['nombre']};NUEVO01;{e['destinos'][1]['nombre']};12,5;3;7000;7400\nX;OTRO;Destino inexistente;1;1;1;1\n"
    r = c.post("/api/v1/tarifas/importar", params={"modo": "previsualizar"}, files={"archivo": ("t.csv", csv.encode(), "text/csv")}, headers=hj)
    assert r.status_code == 200 and len(r.json()["validas"]) == 1 and len(r.json()["errores"]) == 1 and r.json()["rodales_nuevos"] == ["NUEVO01"]
    r = c.post("/api/v1/tarifas/importar", params={"modo": "confirmar"}, files={"archivo": ("t.csv", csv.encode(), "text/csv")}, headers=hj)
    assert r.json()["aplicadas"] == 1
    assert c.delete(f"/api/v1/rodales/{rid}", headers=hj).status_code == 200
    # remito manual del transportista: tarifa por tracción (6x4) y duplicado
    ht, _ = login("transp.hector")
    et = c.get("/api/v1/estado", params={"rol": "transportista"}, headers=ht).json()
    cam = et["camiones"][0]
    et = c.get("/api/v1/estado", params={"rol": "transportista", "camion_id": cam["id"]}, headers=ht).json()
    rod = next(r for r in et["rodales"] if r["codigo"] == "PIEDIESEL")
    t = next(t for t in et["tarifas"] if t["rodal_id"] == rod["id"] and t["destino_id"] == did)
    num = "T-" + dt.datetime.now().strftime("%H%M%S")
    r = c.post("/api/v1/remitos", json={"camion_id": cam["id"], "numero": num, "rodal_id": rod["id"], "destino_id": did, "toneladas": 27.4}, headers=ht)
    assert r.status_code == 201 and r.json()["importe"] == round(t["tarifa_6x4"] * 27.4), r.text
    rem = r.json()["id"]
    # edición de remito conservando id y recalculando tarifa * toneladas
    r_ed = c.put(f"/api/v1/remitos/{rem}", json={"numero": num, "rodal_id": rod["id"], "destino_id": did, "toneladas": 30.0}, headers=ht)
    assert r_ed.status_code == 200 and r_ed.json()["importe"] == round(t["tarifa_6x4"] * 30.0)
    assert c.post("/api/v1/remitos", json={"camion_id": cam["id"], "numero": num, "rodal_id": rod["id"], "toneladas": 1}, headers=ht).status_code == 409
    r = c.post("/api/v1/remitos", json={"camion_id": cam["id"], "rodal_id": rod["id"], "toneladas": 20}, headers=ht)
    assert r.status_code == 201 and r.json()["importe"] is None  # sin destino -> sin tarifa
    sin = r.json()["id"]
    f = c.get(f"/api/v1/camiones/{cam['id']}/facturacion", headers=ht).json()
    assert f["mes"]["sin_tarifa"] >= 1 and len(f["serie"]) == 6
    r = c.get(f"/api/v1/camiones/{cam['id']}/reportes/fletes.pdf", headers=ht)
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    hr, _ = login("transp.raul")
    assert c.delete(f"/api/v1/remitos/{rem}", headers=hr).status_code == 403
    assert c.delete(f"/api/v1/remitos/{rem}", headers=ht).status_code == 200
    assert c.delete(f"/api/v1/remitos/{sin}", headers=ht).status_code == 200
    # foto inválida
    r = c.post("/api/v1/remitos/foto", params={"camion_id": cam["id"]}, files={"archivo": ("x.jpg", b"no es imagen", "image/jpeg")}, headers=ht)
    assert r.status_code == 415


def test_registro_y_admin():
    u = "nuevo." + dt.datetime.now().strftime("%H%M%S")
    r = c.post("/api/v1/auth/registro", json={"usuario": u, "password": "Clave.12345", "nombre": "Juan Prueba", "empresa": "Transp. Prueba", "tipo_empresa": "transporte", "puesto": "Chofer"})
    assert r.status_code == 201
    assert c.post("/api/v1/auth/login", json={"usuario": u, "password": "Clave.12345"}).status_code == 403
    ha = login_admin()
    lista = c.get("/api/v1/usuarios", headers=ha).json()
    uid = next(x["id"] for x in lista if x["usuario"] == u)
    assert c.put(f"/api/v1/usuarios/{uid}", json={"activo": True}, headers=ha).status_code == 200
    s = c.post("/api/v1/auth/login", json={"usuario": u, "password": "Clave.12345"})
    assert s.status_code == 200 and s.json()["usuario"]["roles"] == ["transportista"]
    assert c.put(f"/api/v1/usuarios/{uid}", json={"activo": False}, headers=ha).status_code == 200


def login_admin():
    r = c.post("/api/v1/auth/login", json={"usuario": os.getenv("ADMIN_USUARIO", "admin"), "password": os.getenv("ADMIN_PASSWORD", "Admin.2026")})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["access_token"]}
