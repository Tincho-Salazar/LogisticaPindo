"""Borra TODOS los datos de las tablas ZTLOGI_* y vuelve a cargar los datos de ejemplo. Sólo dev/staging.

Uso:  .venv\\Scripts\\python scripts\\reset_demo.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config, db  # noqa: E402
import init_db, seed_demo  # noqa: E402

ORDEN = ["ZTLOGI_AUDITORIA", "ZTLOGI_DISPOSITIVOS", "ZTLOGI_REFRESH_TOKENS", "ZTLOGI_REMITO_BORRADORES", "ZTLOGI_REMITOS", "ZTLOGI_TARIFAS",
         "ZTLOGI_BASCULA_MOV", "ZTLOGI_BASCULA_TURNOS", "ZTLOGI_BASCULA_DESCANSOS", "ZTLOGI_CARGA_LINEAS", "ZTLOGI_CARGAS", "ZTLOGI_INICIOS_DIA",
         "ZTLOGI_PEDIDO_LINEAS", "ZTLOGI_PEDIDOS", "ZTLOGI_INICIO_CARGA", "ZTLOGI_SOLICITUDES_UNIDADES", "ZTLOGI_PRIORIDAD_FRENTE",
         "ZTLOGI_PROGRAMA_EMISIONES", "ZTLOGI_PROGRAMA", "ZTLOGI_PILAS_HIST", "ZTLOGI_PILAS", "ZTLOGI_DISPONIBILIDAD", "ZTLOGI_INCIDENCIAS",
         "ZTLOGI_CAMIONES", "ZTLOGI_USUARIOS", "ZTLOGI_RODALES", "ZTLOGI_LARGOS", "ZTLOGI_ESPECIES", "ZTLOGI_DESTINOS", "ZTLOGI_CONTRATISTAS"]


def main():
    if config.APP_ENV == "prod":
        raise SystemExit("reset_demo no se ejecuta en producción")
    with db.tx() as cn:
        for t in ORDEN:
            db.run(cn, f"DELETE FROM dbo.{t}")
    init_db.main()
    seed_demo.main()


if __name__ == "__main__":
    main()
