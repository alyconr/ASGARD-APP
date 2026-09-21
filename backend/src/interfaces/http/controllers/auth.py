"""Authentication and user management controller."""

from __future__ import annotations

import hashlib
import time
import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import RolUsuario
from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.models.auth import Rol, UserSession, Usuario
from src.infrastructure.db.models.organizacion import Coordinacion, Especialidad
from src.infrastructure.db.session import get_async_session
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.security.cookie_auth import (
    clear_auth_refresh_cookie,
    set_auth_refresh_cookie,
    verify_csrf_origin,
)
from src.infrastructure.security.jwt import create_access_token, create_refresh_token, decode_token
from src.infrastructure.security.password import hash_password, verify_password
from src.interfaces.http.deps import get_current_user, require_roles
from src.interfaces.http.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# In-memory sliding-window tracker for login rate limiting: key -> list of failure timestamps
_login_failures: dict[str, list[float]] = {}


def _check_rate_limit(key: str, max_attempts: int = 5, window_seconds: int = 60) -> None:
    now = time.time()
    failures = [t for t in _login_failures.get(key, []) if now - t < window_seconds]
    _login_failures[key] = failures
    if len(failures) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos de acceso fallidos. Por favor espere un momento antes de reintentar.",
        )


def _record_login_failure(key: str) -> None:
    now = time.time()
    _login_failures.setdefault(key, []).append(now)


def _clear_login_failures(key: str) -> None:
    _login_failures.pop(key, None)


def _map_user_response(user: Usuario) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        telefono=user.telefono,
        activo=user.activo,
        roles=list(user.role_names),
        coordinacion=user.coordinacion,
        especialidad=user.especialidad,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    """Authenticate with email and password and return tokens with HttpOnly cookie."""
    client_ip = request.client.host if request.client else "unknown"
    email_clean = payload.email.strip().lower()
    rate_limit_key = f"{client_ip}:{email_clean}"
    _check_rate_limit(rate_limit_key)

    audit_repo = AuditRepository(session)
    stmt = (
        select(Usuario)
        .where(Usuario.email == email_clean)
        .options(
            selectinload(Usuario.roles),
            selectinload(Usuario.coordinacion),
            selectinload(Usuario.especialidad),
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None or not verify_password(payload.password, user.hashed_password):
        _record_login_failure(rate_limit_key)
        if user:
            await audit_repo.add_event(
                entidad="Usuario",
                entidad_id=user.id,
                accion="LOGIN_FAILED",
                detalle={"ip": client_ip, "motivo": "Contraseña inválida"},
            )
            await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not user.activo:
        await audit_repo.add_event(
            entidad="Usuario",
            entidad_id=user.id,
            accion="LOGIN_FAILED",
            detalle={"ip": client_ip, "motivo": "Cuenta desactivada"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta de usuario inactiva",
        )

    _clear_login_failures(rate_limit_key)

    token_family = uuid.uuid4()
    jti = str(uuid.uuid4())
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "roles": list(user.role_names),
        "token_version": getattr(user, "token_version", 1),
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token({
        **token_data,
        "jti": jti,
        "token_family": str(token_family),
    })

    settings = get_settings()
    now = datetime.now(UTC)
    new_session = UserSession(
        usuario_id=user.id,
        refresh_token_hash=_hash_token(refresh_token),
        token_family=token_family,
        jti=jti,
        expires_at=now + timedelta(days=settings.jwt_refresh_token_expire_days),
        ip_address=client_ip if client_ip != "unknown" else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(new_session)

    # Set HttpOnly refresh cookie for browser security
    set_auth_refresh_cookie(response, refresh_token)

    await audit_repo.add_event(
        entidad="Usuario",
        entidad_id=user.id,
        accion="LOGIN_SUCCESS",
        detalle={"ip": client_ip},
    )
    await session.commit()

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=_map_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UserResponse:
    """Return profile and scoping information for current authenticated user."""
    return _map_user_response(current_user)


@router.post("/refresh", dependencies=[Depends(verify_csrf_origin)])
async def refresh_token(
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    asgard_refresh_token: str | None = Cookie(None),
) -> dict[str, Any]:
    """Exchange a valid refresh token for a new access token and rotated refresh token with replay protection."""
    raw_token = asgard_refresh_token
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco no proporcionado en cookie de sesión",
        )

    try:
        decoded = decode_token(raw_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    if decoded.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tipo de token no válido para refresco",
        )

    try:
        user_id = uuid.UUID(decoded["sub"])
    except (ValueError, KeyError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene identificador de usuario válido",
        )

    user = await session.get(
        Usuario,
        user_id,
        options=[
            selectinload(Usuario.roles),
            selectinload(Usuario.coordinacion),
            selectinload(Usuario.especialidad),
        ],
    )
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inválido o inactivo",
        )

    # Validate token_version revocation
    token_ver = decoded.get("token_version")
    if token_ver is not None and token_ver != getattr(user, "token_version", 1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token de refresco fue revocado o expiró",
        )

    # Locate active UserSession by jti or hash
    jti = decoded.get("jti")
    token_hash = _hash_token(raw_token)
    audit_repo = AuditRepository(session)

    if jti:
        sess_stmt = select(UserSession).where(UserSession.jti == jti).with_for_update()
    else:
        sess_stmt = select(UserSession).where(UserSession.refresh_token_hash == token_hash).with_for_update()

    sess_res = await session.execute(sess_stmt)
    user_sess = sess_res.scalar_one_or_none()

    now = datetime.now(UTC)

    # REPLAY ATTACK DETECTION
    if user_sess is not None and user_sess.revoked_at is not None:
        # Replay detected! Invalidate entire family and bump token_version immediately
        revoke_stmt = (
            select(UserSession)
            .where(
                UserSession.token_family == user_sess.token_family,
                UserSession.revoked_at.is_(None),
            )
            .with_for_update()
        )
        family_res = await session.execute(revoke_stmt)
        for s in family_res.scalars().all():
            s.revoked_at = now

        user.token_version = getattr(user, "token_version", 1) + 1
        clear_auth_refresh_cookie(response)
        await audit_repo.add_event(
            entidad="Usuario",
            entidad_id=user.id,
            accion="REFRESH_TOKEN_REPLAY_DETECTED",
            detalle={"token_family": str(user_sess.token_family), "jti": jti},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco reutilizado. Todas las sesiones de esta familia han sido revocadas por seguridad.",
        )

    if user_sess is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión no válida o no encontrada",
        )

    if user_sess.expires_at < now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de refresco expirado",
        )

    # Single-use rotation: revoke the consumed session
    user_sess.revoked_at = now

    # Issue new refresh token within the same token_family
    new_jti = str(uuid.uuid4())
    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "roles": list(user.role_names),
        "token_version": getattr(user, "token_version", 1),
    }
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token({
        **token_data,
        "jti": new_jti,
        "token_family": str(user_sess.token_family),
    })

    settings = get_settings()
    client_ip = request.client.host if request.client else None
    rotated_session = UserSession(
        usuario_id=user.id,
        refresh_token_hash=_hash_token(new_refresh_token),
        token_family=user_sess.token_family,
        jti=new_jti,
        expires_at=now + timedelta(days=settings.jwt_refresh_token_expire_days),
        ip_address=client_ip if client_ip != "unknown" else None,
        user_agent=request.headers.get("user-agent"),
    )
    session.add(rotated_session)
    await session.commit()

    set_auth_refresh_cookie(response, new_refresh_token)

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "user": _map_user_response(user).model_dump(),
    }



@router.post("/logout", dependencies=[Depends(verify_csrf_origin)])
async def logout(
    response: Response,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """Revoke user session immediately by incrementing token_version, revoking DB sessions, and clearing cookie."""
    now = datetime.now(UTC)
    current_user.token_version = getattr(current_user, "token_version", 1) + 1

    stmt = select(UserSession).where(
        UserSession.usuario_id == current_user.id,
        UserSession.revoked_at.is_(None),
    )
    active_sessions = (await session.execute(stmt)).scalars().all()
    for s in active_sessions:
        s.revoked_at = now

    clear_auth_refresh_cookie(response)

    audit_repo = AuditRepository(session)
    await audit_repo.add_event(
        entidad="Usuario",
        entidad_id=current_user.id,
        accion="LOGOUT",
        detalle={"email": current_user.email},
    )
    await session.commit()
    return {"message": "Sesión cerrada exitosamente"}


@router.post("/change-password", dependencies=[Depends(verify_csrf_origin)])
async def change_password(
    response: Response,
    payload: ChangePasswordRequest,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """Change current user password, invalidating all existing sessions and revoking tokens."""
    if payload.new_password != payload.confirm_new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña y su confirmación no coinciden",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La nueva contraseña debe tener al menos 8 caracteres",
        )

    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña actual es incorrecta",
        )

    now = datetime.now(UTC)
    current_user.hashed_password = hash_password(payload.new_password)
    current_user.token_version = getattr(current_user, "token_version", 1) + 1

    stmt = select(UserSession).where(
        UserSession.usuario_id == current_user.id,
        UserSession.revoked_at.is_(None),
    )
    active_sessions = (await session.execute(stmt)).scalars().all()
    for s in active_sessions:
        s.revoked_at = now

    clear_auth_refresh_cookie(response)

    audit_repo = AuditRepository(session)
    await audit_repo.add_event(
        entidad="Usuario",
        entidad_id=current_user.id,
        accion="PASSWORD_CHANGED",
        detalle={"email": current_user.email},
    )
    await session.commit()
    return {"message": "Contraseña actualizada exitosamente. Todas las sesiones activas han sido invalidadas."}



@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def create_user(
    payload: UserCreateRequest,
    current_user: Annotated[Usuario, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserResponse:
    """Register a new user enforcing privilege escalation restrictions and organizational invariants."""
    # Privilege escalation prevention: ADMIN cannot create SUPERADMIN
    if RolUsuario.SUPERADMIN.value in payload.roles and not current_user.has_role(RolUsuario.SUPERADMIN.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo un SUPERADMIN puede asignar o crear usuarios con rol SUPERADMIN",
        )

    email_clean = payload.email.strip().lower()
    existing = await session.execute(select(Usuario).where(Usuario.email == email_clean))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El correo electrónico ya se encuentra registrado",
        )

    # Invariant: Líder o Usuario Adicional REQUIEREN coordinación y especialidad
    needs_org = any(
        r in [RolUsuario.LIDER_EQUIPO_EJECUTOR.value, RolUsuario.USUARIO_ADICIONAL.value]
        for r in payload.roles
    )
    if needs_org:
        if not payload.coordinacion_id or not payload.especialidad_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Líder y Usuario Adicional requieren asignación obligatoria de Coordinación y Especialidad",
            )
        # Check specialty belongs to coordination
        esp = await session.get(Especialidad, payload.especialidad_id)
        if esp is None or esp.coordinacion_id != payload.coordinacion_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La especialidad seleccionada no pertenece a la coordinación especificada",
            )

    new_user = Usuario(
        email=email_clean,
        hashed_password=hash_password(payload.password),
        nombre=payload.nombre.strip(),
        apellido=payload.apellido.strip(),
        telefono=payload.telefono.strip() if payload.telefono else None,
        coordinacion_id=payload.coordinacion_id,
        especialidad_id=payload.especialidad_id,
        activo=True,
        token_version=1,
    )
    session.add(new_user)
    await session.flush()

    if payload.roles:
        roles_stmt = select(Rol).where(Rol.nombre.in_(payload.roles))
        roles_res = await session.execute(roles_stmt)
        roles = list(roles_res.scalars().all())
        new_user.roles = roles

    audit_repo = AuditRepository(session)
    await audit_repo.add_event(
        entidad="Usuario",
        entidad_id=new_user.id,
        accion="ROLE_ASSIGNED",
        detalle={"creado_por": str(current_user.id), "roles": payload.roles},
    )
    await session.commit()
    await session.refresh(new_user, attribute_names=["roles", "coordinacion", "especialidad"])
    return _map_user_response(new_user)


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def list_users(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    role: str | None = Query(None),
    coordinacion_id: uuid.UUID | None = Query(None),
    especialidad_id: uuid.UUID | None = Query(None),
) -> list[UserResponse]:
    """List users filtered by role, coordination, or specialty."""
    stmt = (
        select(Usuario)
        .options(
            selectinload(Usuario.roles),
            selectinload(Usuario.coordinacion),
            selectinload(Usuario.especialidad),
        )
        .order_by(Usuario.nombre, Usuario.apellido)
    )
    if coordinacion_id:
        stmt = stmt.where(Usuario.coordinacion_id == coordinacion_id)
    if especialidad_id:
        stmt = stmt.where(Usuario.especialidad_id == especialidad_id)
    result = await session.execute(stmt)
    users = result.scalars().all()
    if role:
        users = [u for u in users if role in u.role_names]
    return [_map_user_response(u) for u in users]
