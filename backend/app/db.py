"""Acceso a SQL Server con pyodbc. Consultas parametrizadas siempre (nunca concatenar valores)."""
import datetime as dt
import decimal
import uuid
from contextlib import contextmanager

import pyodbc

from . import config


def _conn_str():
    base = (
        f"DRIVER={{{config.DB_DRIVER}}};SERVER={config.DB_SERVER};DATABASE={config.DB_NAME};"
        "TrustServerCertificate=yes;"
    )
    if config.DB_TRUSTED:
        return base + "Trusted_Connection=yes;"
    return base + f"UID={config.DB_USER};PWD={config.DB_PASSWORD};"


def _guid(raw):
    return str(uuid.UUID(bytes_le=raw))


def connect():
    cn = pyodbc.connect(_conn_str(), autocommit=False, timeout=10)
    cn.add_output_converter(-11, _guid)  # SQL_GUID -> str en minúsculas
    return cn


@contextmanager
def tx():
    """Transacción: commit al salir sin error, rollback si hay excepción."""
    cn = connect()
    try:
        yield cn
        cn.commit()
    except Exception:
        cn.rollback()
        raise
    finally:
        cn.close()


def _py(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, dt.datetime):
        return v.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, dt.time):
        return v.strftime("%H:%M")
    if isinstance(v, bytes):
        return v.hex()
    return v


def rows(cn, sql, *params):
    cur = cn.cursor()
    cur.execute(sql, params)
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, (_py(v) for v in r))) for r in cur.fetchall()]


def one(cn, sql, *params):
    r = rows(cn, sql, *params)
    return r[0] if r else None


def scalar(cn, sql, *params):
    cur = cn.cursor()
    cur.execute(sql, params)
    r = cur.fetchone()
    return _py(r[0]) if r else None


def run(cn, sql, *params):
    cur = cn.cursor()
    cur.execute(sql, params)
    return cur.rowcount
