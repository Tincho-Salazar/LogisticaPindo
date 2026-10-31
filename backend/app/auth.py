"""Autenticación (Argon2 + JWT) y autorización por rol. Nunca confiar en filtros del cliente."""
import datetime as dt
import hashlib
import secrets

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, Request

from . import config, db
from .util import ApiError, ahora, nuevo_id

ph = PasswordHasher()
ROLES = ("transportista", "elaborador", "supervisor", "bascula", "jefe", "admin")
PUESTOS = ("Capataz", "Mecánico", "Maquinista", "Chofer", "Supervisor", "Jefe de Área Forestal", "Otro")
TIPOS_EMPRESA = ("transporte", "elaborador", "pindo")


def hash_password(p):
    return ph.hash(p)


def verify_password(h, p):
    try:
        return ph.verify(h, p)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def roles_derivados(tipo_empresa, puesto):
    """Sección 5.2 del README: roles habilitados según rubro y puesto."""
    if tipo_empresa == "transporte":
        return ["transportista"]
    if tipo_empresa == "elaborador":
        return ["elaborador"]
    if puesto == "Jefe de Área Forestal":
        return ["jefe"]
    if puesto == "Supervisor":
        return ["supervisor", "bascula"]
    return ["bascula"]


def roles_de(user):
    r = [x for x in (user.get("roles") or "").split(",") if x]
    if "admin" in r:  # el administrador entra a todos los perfiles
        return list(ROLES)
    if config.MODO_PRUEBA:
        r = list(dict.fromkeys(r + ["transportista", "elaborador", "supervisor", "bascula", "jefe"]))
    return r


def crear_access(user):
    exp = dt.datetime.now(dt.timezone.utc) + dt.timedelta(minutes=config.JWT_ACCESS_MIN)
    return jwt.encode({"sub": user["id"], "usr": user["usuario"], "exp": exp}, config.JWT_SECRET, algorithm="HS256")


def _h(t):
    return hashlib.sha256(t.encode()).hexdigest()


def emitir_refresh(cn, user, familia=None, dispositivo=None):
    raw = secrets.token_urlsafe(48)
    db.run(
        cn,
        "INSERT INTO dbo.ZTLOGI_REFRESH_TOKENS (id, usuario_id, token_hash, familia, expira, dispositivo, created_at) VALUES (?,?,?,?,?,?,?)",
        nuevo_id(), user["id"], _h(raw), familia or nuevo_id(),
        ahora() + dt.timedelta(days=config.JWT_REFRESH_DAYS), (dispositivo or "")[:160], ahora(),
    )
    return raw


def rotar_refresh(cn, raw):
    """Rota el refresh token. Si se reutiliza uno ya rotado, se revoca toda la familia (robo de token)."""
    t = db.one(cn, "SELECT * FROM dbo.ZTLOGI_REFRESH_TOKENS WHERE token_hash = ?", _h(raw or ""))
    if not t:
        raise ApiError(401, "refresh_invalido", "Sesión inválida, volvé a ingresar")
    if t["revocado"]:
        db.run(cn, "UPDATE dbo.ZTLOGI_REFRESH_TOKENS SET revocado = 1 WHERE familia = ?", t["familia"])
        cn.commit()  # la revocación debe persistir aunque la respuesta sea un error
        raise ApiError(401, "refresh_reutilizado", "Sesión revocada por seguridad, volvé a ingresar")
    if dt.datetime.fromisoformat(t["expira"]) < ahora():
        raise ApiError(401, "refresh_vencido", "Sesión vencida, volvé a ingresar")
    db.run(cn, "UPDATE dbo.ZTLOGI_REFRESH_TOKENS SET revocado = 1 WHERE id = ?", t["id"])
    user = cargar_usuario(cn, t["usuario_id"])
    if not user or not user["activo"]:
        raise ApiError(403, "usuario_inactivo", "Usuario inactivo")
    return user, emitir_refresh(cn, user, familia=t["familia"], dispositivo=t["dispositivo"])


def revocar_refresh(cn, raw):
    db.run(cn, "UPDATE dbo.ZTLOGI_REFRESH_TOKENS SET revocado = 1 WHERE token_hash = ?", _h(raw or ""))


def cargar_usuario(cn, uid):
    u = db.one(
        cn,
        "SELECT u.*, c.nombre AS contratista FROM dbo.ZTLOGI_USUARIOS u "
        "LEFT JOIN dbo.ZTLOGI_CONTRATISTAS c ON c.id = u.contratista_id WHERE u.id = ?",
        uid,
    )
    if u:
        u.pop("password_hash", None)
        u["roles_lista"] = roles_de(u)
    return u


def login(cn, usuario, password):
    u = db.one(cn, "SELECT * FROM dbo.ZTLOGI_USUARIOS WHERE usuario = ?", (usuario or "").strip().lower())
    generico = ApiError(401, "credenciales", "Usuario o contraseña incorrectos")
    if not u:
        verify_password(ph.hash("x"), password)  # mismo tiempo de respuesta exista o no el usuario
        raise generico
    if u["bloqueado_hasta"] and dt.datetime.fromisoformat(u["bloqueado_hasta"]) > ahora():
        raise ApiError(429, "bloqueado", "Demasiados intentos. Esperá unos minutos y volvé a probar")
    if not verify_password(u["password_hash"], password):
        n = u["intentos_fallidos"] + 1
        bloqueo = ahora() + dt.timedelta(minutes=min(60, 2 ** (n - 5))) if n >= 5 else None
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?", n, bloqueo, u["id"])
        cn.commit()
        raise generico
    if not u["activo"]:
        raise ApiError(403, "pendiente_aprobacion", "Tu usuario todavía no fue aprobado por un administrador")
    db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET intentos_fallidos = 0, bloqueado_hasta = NULL, ultimo_acceso = ? WHERE id = ?", ahora(), u["id"])
    return cargar_usuario(cn, u["id"])


# ---------- dependencias FastAPI ----------

def conn():
    with db.tx() as cn:
        yield cn


def usuario_actual(request: Request, cn=Depends(conn)):
    h = request.headers.get("authorization", "")
    if not h.lower().startswith("bearer "):
        raise ApiError(401, "no_autenticado", "Iniciá sesión")
    try:
        data = jwt.decode(h[7:].strip(), config.JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise ApiError(401, "token_vencido", "Sesión vencida")
    except jwt.PyJWTError:
        raise ApiError(401, "token_invalido", "Sesión inválida")
    u = cargar_usuario(cn, data["sub"])
    if not u or not u["activo"]:
        raise ApiError(403, "usuario_inactivo", "Usuario inactivo")
    u["_cn"] = cn
    u["_ip"] = request.client.host if request.client else None
    return u


def tiene_rol(user, *roles):
    return bool(set(roles) & set(user["roles_lista"]))


def requiere(*roles):
    def dep(user=Depends(usuario_actual)):
        if not tiene_rol(user, *roles):
            raise ApiError(403, "sin_permiso", "No tenés permiso para esta acción")
        return user
    return dep


def exigir(cond, mensaje="No tenés permiso para esta acción", codigo="sin_permiso", status=403):
    if not cond:
        raise ApiError(status, codigo, mensaje)
