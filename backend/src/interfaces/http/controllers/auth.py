"""Authentication and user management controller."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import RolUsuario
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.organizacion import Coordinacion, Especialidad
from src.infrastructure.db.session import get_async_session
from src.infrastructure.security.jwt import create_access_token, create_refresh_token, decode_token
from src.infrastructure.security.password import hash_password, verify_password
from src.interfaces.http.deps import get_current_user, require_roles
from src.interfaces.http.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    UserCreateRequest,
    UserResponse,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


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
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    """Authenticate with email and password and return tokens."""
    email_clean = payload.email.strip().lower()
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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales incorrectas",
        )

    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cuenta de usuario inactiva",
        )

    token_data = {
        "sub": str(user.id),
        "email": user.email,
        "roles": list(user.role_names),
    }
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=_map_user_response(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[Usuario, Depends(get_current_user)],
) -> UserResponse:
    """Return profile and scoping information for current authenticated user."""
    return _map_user_response(current_user)


@router.post("/refresh")
async def refresh_token(
    payload: RefreshTokenRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """Exchange a valid refresh token for a new access token."""
    try:
        decoded = decode_token(payload.refresh_token)
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

    user_id = uuid.UUID(decoded["sub"])
    user = await session.get(Usuario, user_id, options=[selectinload(Usuario.roles)])
    if user is None or not user.activo:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inválido o inactivo",
        )

    new_token = create_access_token({
        "sub": str(user.id),
        "email": user.email,
        "roles": list(user.role_names),
    })
    return {"access_token": new_token, "token_type": "bearer"}


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value))],
)
async def create_user(
    payload: UserCreateRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> UserResponse:
    """Register a new user enforcing organizational invariants."""
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
    )
    session.add(new_user)
    await session.flush()

    if payload.roles:
        roles_stmt = select(Rol).where(Rol.nombre.in_(payload.roles))
        roles_res = await session.execute(roles_stmt)
        roles = list(roles_res.scalars().all())
        new_user.roles = roles

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
