# Requiere el servidor corriendo (run.bat) y la base demo recien sembrada (scripts/reset_demo.py). Uso: .venv/Scripts/python tests/ui/ui_walk.py
"""Recorre la PWA como cada rol y reporta errores de consola / render."""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(__file__).parent / "capturas"
OUT.mkdir(exist_ok=True)
import os
BASE = os.getenv("TEST_BASE", "http://127.0.0.1:8080")
errores = []


def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)


def check(page, ctx):
    t = page.inner_text("#app")
    for bad in ("No se pudo dibujar", "undefined", "NaN", "[object Object]"):
        if bad in t:
            errores.append(f"{ctx}: texto sospechoso '{bad}'")


def login(page, u):
    page.goto(BASE)
    page.evaluate("localStorage.clear()")
    page.goto(BASE)
    page.fill("#lg-u", u)
    page.fill("#lg-p", "Demo.2026" if u != "admin" else "Admin.2026")
    page.click("button[type=submit]")
    page.wait_for_selector(".rolcard", timeout=8000)


def tabs(page, ctx, names):
    for n in names:
        page.click(f'button.tab[data-v="{n}"]')
        page.wait_for_timeout(700)
        check(page, f"{ctx}/{n}")
        shot(page, f"{ctx}_{n}")


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 412, "height": 915}, device_scale_factor=1)
    page.on("console", lambda m: errores.append(f"console {m.type}: {m.text}") if m.type == "error" else None)
    page.on("pageerror", lambda e: errores.append(f"pageerror: {e}"))

    # supervisor
    login(page, "sup.ana")
    page.click('button[data-action="rol"][data-v="supervisor"]')
    page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1200)
    tabs(page, "sup", ["stock", "camiones", "programa", "pedidos", "analisis"])
    for v in ["destino", "cruce", "transp", "tcarga", "demoras", "traza"]:
        page.click(f'button[data-action="avista"][data-v="{v}"]'); page.wait_for_timeout(500); check(page, f"sup/analisis/{v}")
    shot(page, "sup_analisis_traza")
    page.click('button[data-action="tab"][data-v="programa"]'); page.wait_for_timeout(500)
    page.click('button[data-action="fdia"][data-v="hoy"]'); page.wait_for_timeout(500); check(page, "sup/programa/hoy"); shot(page, "sup_programa_hoy")
    page.click('button[data-action="programar"]'); page.wait_for_timeout(500); check(page, "sup/programar"); shot(page, "sup_sheet_programar")
    page.keyboard.press("Escape"); page.wait_for_timeout(300)
    page.click('button[data-action="tab"][data-v="pedidos"]'); page.wait_for_timeout(400)
    page.click('button[data-action="pedido-edit"]'); page.wait_for_timeout(400); check(page, "sup/pedido-sheet"); shot(page, "sup_sheet_pedido"); page.keyboard.press("Escape")

    # elaborador
    login(page, "elab.marcos")
    page.click('button[data-action="rol"][data-v="elaborador"]')
    page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1200)
    tabs(page, "elab", ["stock", "cola", "programa", "pedido"])
    page.click('button[data-action="tab"][data-v="stock"]'); page.wait_for_timeout(400)
    page.click('button[data-action="new-pila"]'); page.wait_for_timeout(400); check(page, "elab/pila-sheet"); shot(page, "elab_sheet_pila"); page.keyboard.press("Escape")

    # transportista
    login(page, "transp.hector")
    page.click('button[data-action="rol"][data-v="transportista"]')
    page.wait_for_selector('button[data-action="rol-camion"]', timeout=8000)
    page.click('button[data-action="rol-camion"]')
    page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1200)
    tabs(page, "transp", ["viaje", "programa", "fletes"])
    page.click('button[data-action="tab"][data-v="programa"]'); page.click('button[data-action="fdia"][data-v="manana"]'); page.wait_for_timeout(400); check(page, "transp/programa/manana"); shot(page, "transp_programa_manana")
    page.click('button[data-action="tab"][data-v="fletes"]'); page.wait_for_timeout(400)
    page.click('button[data-action="remito-ver"]'); page.wait_for_timeout(400); check(page, "transp/remito-ver"); shot(page, "transp_sheet_remito"); page.keyboard.press("Escape")
    page.click('button[data-action="remito-manual"]'); page.wait_for_timeout(400); check(page, "transp/remito-manual"); shot(page, "transp_sheet_remito_manual"); page.keyboard.press("Escape")

    # bascula
    login(page, "bascula.rosa")
    page.click('button[data-action="rol"][data-v="bascula"]')
    page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1200)
    tabs(page, "bas", ["pend", "industria", "hist"])

    # jefe
    login(page, "jefe.carlos")
    page.click('button[data-action="rol"][data-v="jefe"]')
    page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1200)
    tabs(page, "jefe", ["tarifas"])
    page.click('button[data-action="tarifa-edit"]'); page.wait_for_timeout(400); check(page, "jefe/tarifa-sheet"); shot(page, "jefe_sheet_tarifa"); page.keyboard.press("Escape")
    page.click('button[data-action="importar"]'); page.wait_for_timeout(400); check(page, "jefe/importar"); shot(page, "jefe_sheet_importar"); page.keyboard.press("Escape")
    page.click('button[data-action="cambiar-rol"]'); page.wait_for_timeout(400)
    page.click('button[data-action="rol"][data-v="transportista"]'); page.wait_for_selector('button[data-action="rol-camion"]', timeout=8000)
    page.click('button[data-action="rol-camion"]'); page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1000)
    tabs(page, "jefe_transp", ["viaje", "fletes"])
    page.click('button[data-action="cambiar-rol"]'); page.wait_for_timeout(400)
    page.click('button[data-action="rol"][data-v="elaborador"]'); page.wait_for_selector('button[data-action="rol-contr"]', timeout=8000)
    page.click('button[data-action="rol-contr"]'); page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1000)
    tabs(page, "jefe_elab", ["stock", "cola", "pedido"])

    # admin
    login(page, "admin")
    page.click('button[data-action="rol"][data-v="admin"]')
    page.wait_for_selector("nav.nav", timeout=8000); page.wait_for_timeout(1500)
    tabs(page, "admin", ["usuarios", "catalogos"])
    page.click('button[data-action="tab"][data-v="usuarios"]'); page.wait_for_timeout(500)
    page.click('button[data-action="usuario-edit"]'); page.wait_for_timeout(400); check(page, "admin/usuario-sheet"); shot(page, "admin_sheet_usuario"); page.keyboard.press("Escape")
    b.close()

print("ERRORES:", len(errores))
for e in errores:
    print(" -", e)
sys.exit(1 if errores else 0)
