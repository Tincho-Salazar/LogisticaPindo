# Requiere el servidor corriendo (run.bat) y la base demo recien sembrada (scripts/reset_demo.py). Uso: .venv/Scripts/python tests/ui/ui_flow.py
"""Flujo de un día desde la interfaz + prueba de modo sin conexión (outbox)."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "capturas"
import os
BASE = os.getenv("TEST_BASE", "http://127.0.0.1:8080")
errores = []


def login(page, u, pw="Demo.2026"):
    page.goto(BASE); page.evaluate("localStorage.clear()"); page.goto(BASE)
    page.fill("#lg-u", u); page.fill("#lg-p", pw); page.click("button[type=submit]")
    page.wait_for_selector(".rolcard", timeout=8000)


def texto(page):
    return page.inner_text("#app")


with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 412, "height": 915})
    page = ctx.new_page()
    page.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))
    page.on("console", lambda m: errores.append(f"console: {m.text}") if m.type == "error" and "ERR_INTERNET_DISCONNECTED" not in m.text else None)

    # 1. transportista entra en fila
    login(page, "transp.hector")
    page.click('button[data-action="rol"][data-v="transportista"]'); page.wait_for_selector('button[data-action="rol-camion"]'); page.click('button[data-action="rol-camion"]')
    page.wait_for_selector('button[data-action="entrar-fila"]', timeout=8000); page.click('button[data-action="entrar-fila"]')
    page.wait_for_selector('button[data-action="salir-fila"]', timeout=8000)
    assert "EN FILA DE ESPERA" in texto(page).upper(), "no quedó en fila"

    # 2. elaborador inicia y finaliza la carga
    login(page, "elab.marcos")
    page.click('button[data-action="rol"][data-v="elaborador"]'); page.wait_for_selector("nav.nav"); page.wait_for_timeout(800)
    page.click('button[data-action="tab"][data-v="cola"]'); page.wait_for_timeout(300)
    assert "EN FILA DE ESPERA\n1" in texto(page).upper() or "lleva" in texto(page), "la fila no muestra el camión"
    page.click('button[data-action="iniciar"]'); page.wait_for_selector('button[data-action="finalizar"]', timeout=8000)
    page.click('button[data-action="finalizar"]'); page.wait_for_selector('form[data-form="finalizar"]')
    page.click('input[data-f="circuito"][value="industria"]'); page.wait_for_timeout(300)
    page.fill('input[data-f="m3"][data-i="0"]', "18,6")
    page.click('button[data-action="add-linea"]'); page.wait_for_timeout(200)
    page.click('input[data-f="ltipo"][data-i="1"][value="fino"]'); page.wait_for_timeout(200)
    page.select_option('select[data-f="llargo"][data-i="1"]', "8")
    page.fill('input[data-f="m3"][data-i="1"]', "999")
    page.click('form[data-form="finalizar"] button[type=submit]'); page.wait_for_timeout(300)
    assert "Solo hay" in texto(page), "no validó stock insuficiente en el cliente"
    page.fill('input[data-f="m3"][data-i="1"]', "11,4")
    page.click('form[data-form="finalizar"] button[type=submit]')
    page.wait_for_selector('button[data-action="toggle-carga"]', timeout=8000); page.wait_for_timeout(800)
    page.click('button[data-action="toggle-carga"]'); page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "flow_detalle.png"), full_page=True)
    assert "30,0" in texto(page) and "18,6" in texto(page), "detalle de carga incorrecto: " + texto(page)[:1500]
    page.click('button[data-action="tab"][data-v="stock"]'); page.wait_for_timeout(400)
    assert "123,9" in texto(page), "no descontó stock (142,5 - 18,6)"
    page.screenshot(path=str(OUT / "flow_elab_stock.png"), full_page=True)

    # 3. báscula registra ingreso y salida
    login(page, "bascula.rosa")
    page.click('button[data-action="rol"][data-v="bascula"]'); page.wait_for_selector("nav.nav"); page.wait_for_timeout(800)
    assert "EN CAMINO A BÁSCULA" in texto(page).upper() and "AF 412 KR" in texto(page)
    opt = page.eval_on_selector("select#bi-p", "s => Array.from(s.options).find(o => o.text.includes('AF 412 KR')).value")
    page.select_option("select#bi-p", opt)
    page.click('form[data-form="basing"] button[type=submit]'); page.wait_for_selector('button[data-action="bas-salida"]', timeout=8000)
    page.click('button[data-action="bas-salida"]'); page.wait_for_timeout(1200)
    assert "Permanencia" in texto(page), "no registró la salida"
    page.screenshot(path=str(OUT / "flow_bascula.png"), full_page=True)

    # 4. transportista quedó disponible; prueba sin conexión
    login(page, "transp.hector")
    page.click('button[data-action="rol"][data-v="transportista"]'); page.wait_for_selector('button[data-action="rol-camion"]'); page.click('button[data-action="rol-camion"]')
    page.wait_for_selector("nav.nav"); page.wait_for_timeout(1000)
    assert "DISPONIBLE" in texto(page).upper()
    ctx.set_offline(True); page.wait_for_timeout(300)
    page.click('button[data-action="inc"][data-v="demora"]'); page.wait_for_selector('form[data-form="incidencia"]')
    page.fill('input[name="minutos"]', "25"); page.click('form[data-form="incidencia"] button[type=submit]'); page.wait_for_timeout(800)
    t = texto(page)
    assert "pendiente" in t and "Demora" in t, "la acción offline no quedó pendiente"
    page.screenshot(path=str(OUT / "flow_offline.png"), full_page=True)
    page.reload(); page.wait_for_timeout(1000)
    assert "Sin conexión" in texto(page) and "Demora" in texto(page), "sin conexión no mostró la caché"
    ctx.set_offline(False); page.wait_for_timeout(2500)
    t = texto(page)
    assert "sin enviar" not in t and "Demora" in t, "no sincronizó al volver la conexión: " + t[:300]
    page.screenshot(path=str(OUT / "flow_online.png"), full_page=True)
    b.close()

print("ERRORES:", len(errores))
for e in errores:
    print(" -", e)
print("FLUJO OK")
sys.exit(1 if errores else 0)
