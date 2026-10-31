"""Registro, login, refresco de sesión, perfil y administración de usuarios."""
import re

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field

from .. import auth, db
from ..util import ApiError, ahora, auditar, nuevo_id, uuid_ok

router = APIRouter(tags=["auth"])
USUARIO_RE = re.compile(r"^[a-z0-9._-]{3,40}$")


class Registro(BaseModel):
    usuario: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=8, max_length=128)
    nombre: str = Field(min_length=3, max_length=120)
    empresa: str = Field(min_length=2, max_length=120)
    tipo_empresa: str
    puesto: str


class Login(BaseModel):
    usuario: str = Field(max_length=60)
    password: str = Field(max_length=128)
    dispositivo: str | None = Field(default=None, max_length=160)


class Refresh(BaseModel):
    refresh_token: str = Field(max_length=200)


class EdicionUsuario(BaseModel):
    activo: bool | None = None
    roles: list[str] | None = None
    contratista_id: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    nombre: str | None = Field(default=None, min_length=3, max_length=120)
    empresa: str | None = Field(default=None, min_length=2, max_length=120)


class Perfil(BaseModel):
    nombre: str = Field(min_length=3, max_length=120)
    empresa: str = Field(min_length=2, max_length=120)
    puesto: str


def _sesion(cn, u, dispositivo=None):
    return {"access_token": auth.crear_access(u), "refresh_token": auth.emitir_refresh(cn, u, dispositivo=dispositivo), "usuario": _publico(u)}


def _publico(u):
    return {k: u.get(k) for k in ("id", "usuario", "nombre", "empresa", "tipo_empresa", "puesto", "contratista_id", "contratista", "activo", "ultimo_acceso", "created_at")} | {"roles": u["roles_lista"]}


@router.post("/auth/registro", status_code=201)
def registro(d: Registro, cn=Depends(auth.conn)):
    usuario = d.usuario.strip().lower()
    if not USUARIO_RE.match(usuario):
        raise ApiError(422, "usuario_invalido", "El usuario debe tener 3 a 40 caracteres: letras minúsculas, números, punto, guion")
    if d.tipo_empresa not in auth.TIPOS_EMPRESA:
        raise ApiError(422, "tipo_invalido", "Tipo de empresa inválido")
    if d.puesto not in auth.PUESTOS:
        raise ApiError(422, "puesto_invalido", "Puesto inválido")
    if len(d.nombre.split()) < 2:
        raise ApiError(422, "nombre", "Ingresá nombre y apellido")
    if db.one(cn, "SELECT id FROM dbo.ZTLOGI_USUARIOS WHERE usuario = ?", usuario):
        raise ApiError(409, "usuario_existente", "Ese usuario ya existe")
    uid = nuevo_id()
    db.run(
        cn,
        "INSERT INTO dbo.ZTLOGI_USUARIOS (id, usuario, nombre, password_hash, empresa, tipo_empresa, puesto, roles, activo, created_at, updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,0,?,?)",
        uid, usuario, " ".join(d.nombre.split()), auth.hash_password(d.password), d.empresa.strip(), d.tipo_empresa, d.puesto,
        ",".join(auth.roles_derivados(d.tipo_empresa, d.puesto)), ahora(), ahora(),
    )
    auditar(cn, "usuario", uid, "registro", None, {"usuario": usuario, "tipo_empresa": d.tipo_empresa, "puesto": d.puesto}, None)
    return {"id": uid, "mensaje": "Registro recibido. Un administrador tiene que aprobar tu usuario antes de que puedas ingresar."}


@router.post("/auth/login")
def login(d: Login, request: Request, cn=Depends(auth.conn)):
    u = auth.login(cn, d.usuario, d.password)
    return _sesion(cn, u, d.dispositivo or request.headers.get("user-agent", "")[:160])


@router.post("/auth/refresh")
def refresh(d: Refresh, cn=Depends(auth.conn)):
    u, nuevo = auth.rotar_refresh(cn, d.refresh_token)
    return {"access_token": auth.crear_access(u), "refresh_token": nuevo, "usuario": _publico(u)}


@router.post("/auth/logout")
def logout(d: Refresh, cn=Depends(auth.conn)):
    auth.revocar_refresh(cn, d.refresh_token)
    return {"ok": True}


@router.get("/me")
def me(user=Depends(auth.usuario_actual)):
    return _publico(user)


@router.put("/me")
def editar_me(d: Perfil, user=Depends(auth.usuario_actual)):
    if d.puesto not in auth.PUESTOS:
        raise ApiError(422, "puesto_invalido", "Puesto inválido")
    if len(d.nombre.split()) < 2:
        raise ApiError(422, "nombre", "Ingresá nombre y apellido")
    cn = user["_cn"]
    db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET nombre = ?, empresa = ?, puesto = ?, updated_at = ? WHERE id = ?",
           " ".join(d.nombre.split()), d.empresa.strip(), d.puesto, ahora(), user["id"])
    return _publico(auth.cargar_usuario(cn, user["id"]))


# ---------- administración de usuarios (solo admin) ----------

@router.get("/usuarios")
def usuarios(user=Depends(auth.requiere("admin"))):
    rs = db.rows(user["_cn"], "SELECT u.id, u.usuario, u.nombre, u.empresa, u.tipo_empresa, u.puesto, u.roles, u.contratista_id, c.nombre AS contratista, u.activo, u.ultimo_acceso, u.created_at "
                 "FROM dbo.ZTLOGI_USUARIOS u LEFT JOIN dbo.ZTLOGI_CONTRATISTAS c ON c.id = u.contratista_id ORDER BY u.activo, u.created_at DESC")
    for r in rs:
        r["roles"] = [x for x in (r["roles"] or "").split(",") if x]
    return rs


@router.put("/usuarios/{uid}")
def editar_usuario(uid: str, d: EdicionUsuario, user=Depends(auth.requiere("admin"))):
    cn = user["_cn"]
    uid = uuid_ok(uid)
    u = db.one(cn, "SELECT * FROM dbo.ZTLOGI_USUARIOS WHERE id = ?", uid)
    if not u:
        raise ApiError(404, "no_existe", "Usuario inexistente")
    antes = {k: u[k] for k in ("activo", "roles", "contratista_id", "nombre", "empresa")}
    if d.roles is not None:
        malos = [r for r in d.roles if r not in auth.ROLES]
        if malos:
            raise ApiError(422, "rol_invalido", f"Rol inválido: {', '.join(malos)}")
        if uid == user["id"] and "admin" not in d.roles:
            raise ApiError(409, "admin_propio", "No podés quitarte el rol de administrador")
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET roles = ? WHERE id = ?", ",".join(dict.fromkeys(d.roles)), uid)
    if d.contratista_id is not None:
        cid = uuid_ok(d.contratista_id) if d.contratista_id else None
        if cid and not db.one(cn, "SELECT id FROM dbo.ZTLOGI_CONTRATISTAS WHERE id = ?", cid):
            raise ApiError(422, "contratista", "Contratista inexistente")
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET contratista_id = ? WHERE id = ?", cid, uid)
    if d.activo is not None:
        if uid == user["id"] and not d.activo:
            raise ApiError(409, "admin_propio", "No podés desactivar tu propio usuario")
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET activo = ?, intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?", 1 if d.activo else 0, uid)
        if not d.activo:
            db.run(cn, "UPDATE dbo.ZTLOGI_REFRESH_TOKENS SET revocado = 1 WHERE usuario_id = ?", uid)
    if d.password:
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET password_hash = ? WHERE id = ?", auth.hash_password(d.password), uid)
        db.run(cn, "UPDATE dbo.ZTLOGI_REFRESH_TOKENS SET revocado = 1 WHERE usuario_id = ?", uid)
    if d.nombre:
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET nombre = ? WHERE id = ?", " ".join(d.nombre.split()), uid)
    if d.empresa:
        db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET empresa = ? WHERE id = ?", d.empresa.strip(), uid)
    db.run(cn, "UPDATE dbo.ZTLOGI_USUARIOS SET updated_at = ? WHERE id = ?", ahora(), uid)
    nuevo = auth.cargar_usuario(cn, uid)
    auditar(cn, "usuario", uid, "edicion", antes, {k: nuevo[k] for k in ("activo", "roles", "contratista_id", "nombre", "empresa")}, user, user["_ip"])
    return _publico(nuevo)
