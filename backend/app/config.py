"""Configuración desde variables de entorno (.env)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / os.getenv("LF_ENV", ".env"))  # LF_ENV=.env.prod para apuntar a producción sin tocar .env


def _b(k, d="false"):
    return os.getenv(k, d).strip().lower() in ("1", "true", "yes", "si")


APP_ENV = os.getenv("APP_ENV", "prod")
MODO_PRUEBA = _b("MODO_PRUEBA") and APP_ENV != "prod"  # nunca en producción

DB_SERVER = os.getenv("DB_SERVER", "localhost")
DB_NAME = os.getenv("DB_NAME", "sapinfo")
DB_USER = os.getenv("DB_USER", "")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")
DB_TRUSTED = _b("DB_TRUSTED")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ACCESS_MIN = int(os.getenv("JWT_ACCESS_MIN", "15"))
JWT_REFRESH_DAYS = int(os.getenv("JWT_REFRESH_DAYS", "30"))
ADMIN_USUARIO = os.getenv("ADMIN_USUARIO", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")

TZ = os.getenv("TZ", "America/Argentina/Buenos_Aires")
CIERRE_DISPONIBILIDAD = os.getenv("CIERRE_DISPONIBILIDAD", "20:00")
CIERRE_RELEVAMIENTO = os.getenv("CIERRE_RELEVAMIENTO", "21:00")
TOLERANCIA_DEMORA_MIN = int(os.getenv("TOLERANCIA_DEMORA_MIN", "5"))

DATA_DIR = (BASE_DIR / os.getenv("DATA_DIR", "data")).resolve()
FOTOS_DIR = DATA_DIR / "fotos"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
VISION_MODEL = os.getenv("VISION_MODEL", "claude-opus-5-5")
VISION_DAILY_LIMIT_PER_USER = int(os.getenv("VISION_DAILY_LIMIT_PER_USER", "50"))

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT") or os.getenv("APP_PORT") or "8000")

if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET debe tener al menos 32 caracteres (ver .env.example)")
