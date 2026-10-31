"""Inicializa la base: aplica schema.sql (idempotente), carga catálogos mínimos y crea el administrador del .env.

Uso:  .venv\\Scripts\\python scripts\\init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import auth, config, db  # noqa: E402
from app.util import ahora, nuevo_id  # noqa: E402

ESPECIES = ["Pino Taeda", "Pino Híbrido", "Eucaliptus", "Araucaria"]
LARGOS = [8, 10, 12, 14, 16, 18, 20]


def main():
    sql = (Path(__file__).resolve().parent.parent / "schema.sql").read_text(encoding="utf-8")
    with db.tx() as cn:
        cn.cursor().execute(sql)
        print("Esquema aplicado:", db.scalar(cn, "SELECT COUNT(*) FROM sys.tables WHERE name LIKE 'ZTLOGI%'"), "tablas ZTLOGI_*")
        for e in ESPECIES:
            if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_ESPECIES WHERE nombre = ?", e):
                db.run(cn, "INSERT INTO dbo.ZTLOGI_ESPECIES (id, nombre) VALUES (?,?)", nuevo_id(), e)
        for l in LARGOS:
            if not db.one(cn, "SELECT pies FROM dbo.ZTLOGI_LARGOS WHERE pies = ?", l):
                db.run(cn, "INSERT INTO dbo.ZTLOGI_LARGOS (pies) VALUES (?)", l)
        if not db.one(cn, "SELECT id FROM dbo.ZTLOGI_USUARIOS WHERE usuario = ?", config.ADMIN_USUARIO):
            if len(config.ADMIN_PASSWORD) < 8:
                raise SystemExit("ADMIN_PASSWORD debe tener al menos 8 caracteres en .env")
            db.run(cn, "INSERT INTO dbo.ZTLOGI_USUARIOS (id, usuario, nombre, password_hash, empresa, tipo_empresa, puesto, roles, activo, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,1,?,?)",
                   nuevo_id(), config.ADMIN_USUARIO, "Administrador Sistema", auth.hash_password(config.ADMIN_PASSWORD), "Pindó SA", "pindo", "Otro", "admin,supervisor", ahora(), ahora())
            print("Administrador creado:", config.ADMIN_USUARIO)
        else:
            print("Administrador ya existe:", config.ADMIN_USUARIO)
    print("Listo. Servidor:", config.DB_SERVER, "base:", config.DB_NAME)


if __name__ == "__main__":
    main()
