"""Authentication and authorization FastAPI dependencies."""

from __future__ import annotations

import uuid
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.services.access_scope import AccessScopeService
from src.domain.shared.enums import EstadoUsuario
from src.infrastructure.db.models.auth import Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.security.jwt import decode_token

http_bearer = HTTPBearer(auto_error=False)

PASSWORD_CHANGE_WHITELIST = {
    "/api/v1/auth/me",
    "/api/v1/auth/change-password",
    "/api/v1/auth/logout",
    "/api/v1/auth/refresh",
}


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: Request = None,  # type: ignore
) -> Usuario:
    """Validate Bearer JWT token and return active Usuario ORM instance."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales de autenticación no proporcionadas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token no contiene sujeto válido",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = uuid.UUID(str(user_id_str))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identificador de usuario inválido en token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = (
        select(Usuario)
        .where(Usuario.id == user_id)
        .options(
            selectinload(Usuario.roles),
            selectinload(Usuario.coordinacion),
            selectinload(Usuario.especialidad),
        )
    )
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado en base de datos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate user status
    if getattr(user, "estado", EstadoUsuario.ACTIVO) != EstadoUsuario.ACTIVO:
        if getattr(user, "estado", None) == EstadoUsuario.BLOQUEADO:
            detail = "La cuenta de usuario está bloqueada"
        else:
            detail = "La cuenta de usuario está desactivada"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )

    token_ver = payload.get("token_version")
    if token_ver is not None and token_ver != getattr(user, "token_version", 1):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión ha expirado o fue cerrada",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Invariant 13: Mandatory first access password change
    if getattr(user, "debe_cambiar_password", False) and request is not None:
        path = request.url.path.rstrip("/")
        if path not in PASSWORD_CHANGE_WHITELIST:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debe cambiar su contraseña antes de continuar operando en el sistema",
            )

    return user


async def get_optional_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> Usuario | None:
    """Return user if valid token present, otherwise None without failing."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials, session)
    except HTTPException:
        return None


def require_roles(*allowed_roles: str) -> Callable[[Usuario], Usuario]:
    """Factory creating a role check dependency."""

    def role_checker(user: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
        if not user.has_role(*allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(allowed_roles)}",
            )
        return user

    return role_checker


def get_access_scope_service(
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> AccessScopeService:
    """Provide scoped access verification service."""
    return AccessScopeService(session)
