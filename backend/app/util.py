"""Utilidades: hora de Argentina, jornada operativa, errores uniformes y auditoría."""
import datetime as dt
import json
import uuid
from zoneinfo import ZoneInfo

from . import config, db

ZONA = ZoneInfo(config.TZ)


class ApiError(Exception):
    def __init__(self, status, codigo, mensaje, detalle=None):
        super().__init__(mensaje)
        self.status, self.codigo, self.mensaje, self.detalle = status, codigo, mensaje, detalle or {}


def ahora():
    """Hora actual de Argentina, sin tzinfo (así se guarda en la base)."""
    return dt.datetime.now(ZONA).replace(tzinfo=None, microsecond=0)


def parse_ocurrido(s):
    """Convierte el timestamp del dispositivo (ocurrido_en) en datetime local validado.
    Si es inválido, futuro (>15 min) o de más de 7 días atrás, usa ahora()."""
    srv = ahora()
    if not s:
        return srv
    try:
        t = str(s).strip()
        if t.endswith("Z"):
            d = dt.datetime.fromisoformat(t[:-1]).replace(tzinfo=dt.timezone.utc).astimezone(ZONA).replace(tzinfo=None, microsecond=0)
        else:
            d = dt.datetime.fromisoformat(t)
            if d.tzinfo is not None:
                d = d.astimezone(ZONA).replace(tzinfo=None)
            d = d.replace(microsecond=0)
        if srv - dt.timedelta(days=7) <= d <= srv + dt.timedelta(minutes=15):
            return d
    except Exception:
        pass
    return srv


def hoy():
    return ahora().date()


def manana():
    return hoy() + dt.timedelta(days=1)


def hhmm(d=None):
    return (d or ahora()).strftime("%H:%M")


def mins(s):
    """'07:30' -> 450. Lanza ValueError si el formato es inválido."""
    h, m = str(s).split(":")
    h, m = int(h), int(m)
    if not (0 <= h < 24 and 0 <= m < 60):
        raise ValueError(s)
    return h * 60 + m


def hora_valida(s):
    try:
        return isinstance(s, str) and len(s) == 5 and s[2] == ":" and mins(s) >= 0
    except Exception:
        return False


def cierre_pasado(cierre_hhmm, en=None):
    return mins(hhmm(en)) >= mins(cierre_hhmm)


def jornada_de(s):
    """'hoy' | 'manana' | 'YYYY-MM-DD' -> date."""
    if s in (None, "", "hoy"):
        return hoy()
    if s == "manana":
        return manana()
    try:
        return dt.date.fromisoformat(str(s))
    except ValueError:
        raise ApiError(422, "jornada_invalida", "Jornada inválida")


def nuevo_id():
    return str(uuid.uuid4())


def uuid_ok(s):
    try:
        return str(uuid.UUID(str(s)))
    except Exception:
        raise ApiError(422, "id_invalido", "Identificador inválido")


def redondear1(x):
    return round(float(x) + 1e-9, 1)


def auditar(cn, entidad, entidad_id, accion, antes, despues, usuario, ip=None):
    db.run(
        cn,
        "INSERT INTO dbo.ZTLOGI_AUDITORIA (entidad, entidad_id, accion, antes, despues, usuario_id, en, ip) "
        "VALUES (?,?,?,?,?,?,?,?)",
        entidad,
        str(entidad_id) if entidad_id else None,
        accion,
        json.dumps(antes, ensure_ascii=False, default=str) if antes is not None else None,
        json.dumps(despues, ensure_ascii=False, default=str) if despues is not None else None,
        usuario["id"] if usuario else None,
        ahora(),
        ip,
    )
