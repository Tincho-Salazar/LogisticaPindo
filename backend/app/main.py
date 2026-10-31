"""Logística Forestal Pindó SA · API FastAPI + app móvil (PWA) servida como estáticos."""
import logging
from pathlib import Path

import pyodbc
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .routers import analisis, auth, bascula, camiones, cargas, catalogos, estado, pedidos, programa, remitos, stock, tarifas
from .util import ApiError

log = logging.getLogger("logistica")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

app = FastAPI(title="Logística Forestal Pindó SA", version="1.0.0", docs_url="/api/docs" if config.APP_ENV != "prod" else None, redoc_url=None)
STATIC = Path(__file__).resolve().parent.parent / "static"


@app.exception_handler(ApiError)
async def _api_error(_: Request, e: ApiError):
    return JSONResponse(status_code=e.status, content={"codigo": e.codigo, "mensaje": e.mensaje, "detalle": e.detalle})


@app.exception_handler(pyodbc.Error)
async def _db_error(_: Request, e: pyodbc.Error):
    log.exception("error de base de datos")
    msg = str(e)
    if "UX_ZTLOGI_CAMIONES_patente" in msg:
        return JSONResponse(409, {"codigo": "patente_duplicada", "mensaje": "Ya existe un camión con esa patente", "detalle": {}})
    if "UX_ZTLOGI_REM_numero" in msg:
        return JSONResponse(409, {"codigo": "remito_duplicado", "mensaje": "Ya cargaste un remito con ese número", "detalle": {}})
    return JSONResponse(503, {"codigo": "base_de_datos", "mensaje": "No se pudo acceder a la base de datos", "detalle": {}})


@app.exception_handler(Exception)
async def _any_error(_: Request, e: Exception):
    log.exception("error no controlado")
    return JSONResponse(500, {"codigo": "interno", "mensaje": "Error interno del servidor", "detalle": {}})


@app.middleware("http")
async def _security_headers(request: Request, call_next):
    r = await call_next(request)
    r.headers["X-Content-Type-Options"] = "nosniff"
    r.headers["X-Frame-Options"] = "DENY"
    r.headers["Referrer-Policy"] = "no-referrer"
    r.headers["Permissions-Policy"] = "geolocation=(), microphone=()"
    if not request.url.path.startswith("/api/"):
        r.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; "
            "connect-src 'self'; font-src 'self'; manifest-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        )
    if config.APP_ENV == "prod":
        r.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    if request.url.path.startswith("/api/"):
        r.headers["Cache-Control"] = "no-store"
    return r


for rt in (auth, catalogos, estado, camiones, stock, programa, pedidos, cargas, bascula, tarifas, remitos, analisis):
    app.include_router(rt.router, prefix="/api/v1")


@app.get("/api/v1/app/version")
def version():
    return {"version": app.version, "min_supported_version": "1.0.0", "estado": "ok", "entorno": config.APP_ENV, "modo_prueba": config.MODO_PRUEBA}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html", headers={"Cache-Control": "no-cache"})


@app.get("/sw.js", include_in_schema=False)
def sw():
    return FileResponse(STATIC / "sw.js", media_type="application/javascript", headers={"Cache-Control": "no-cache", "Service-Worker-Allowed": "/"})


app.mount("/static", StaticFiles(directory=STATIC), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, proxy_headers=True, forwarded_allow_ips="*")
