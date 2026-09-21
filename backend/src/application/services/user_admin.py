"""User Administration Service enforcing RBAC, scope invariants, session revocation, and security rules."""

from __future__ import annotations

import math
import uuid
from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.shared.enums import EstadoEquipo, EstadoUsuario, RolUsuario
from src.infrastructure.db.models.auth import Rol, UserSession, Usuario, UsuarioRol
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
)
from src.infrastructure.repositories.audit import AuditRepository
from src.infrastructure.security.password import hash_password
from src.interfaces.http.schemas.auth import (
    PaginatedUsersResponse,
    UserCreateRequest,
    UserResetPasswordRequest,
    UserResponse,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)


def _map_user_response(user: Usuario) -> UserResponse:
    estado_val = user.estado.value if hasattr(getattr(user, "estado", None), "value") else str(getattr(user, "estado", None) or "ACTIVO")
    return UserResponse(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        telefono=user.telefono,
        area=getattr(user, "area", None),
        estado=estado_val,
        activo=user.activo,
        debe_cambiar_password=bool(getattr(user, "debe_cambiar_password", False) or False),
        ultimo_acceso=getattr(user, "ultimo_acceso", None),
        roles=list(user.role_names),
        coordinacion=user.coordinacion,  # type: ignore
        especialidad=user.especialidad,  # type: ignore
    )


class UserAdminService:
    """Service handling multi-user administration, organizational constraints, and credentials."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.audit_repo = AuditRepository(session)

    async def _count_active_superadmins(self) -> int:
        """Count active users holding the SUPERADMIN role."""
        stmt = (
            select(func.count(Usuario.id))
            .join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id)
            .join(Rol, Rol.id == UsuarioRol.rol_id)
            .where(
                Rol.nombre == RolUsuario.SUPERADMIN.value,
                Usuario.estado == EstadoUsuario.ACTIVO,
            )
        )
        res = await self.session.execute(stmt)
        return res.scalar_one() or 0

    async def _revoke_all_sessions(self, user: Usuario) -> None:
        """Bump token_version and mark active UserSession records as revoked."""
        now = datetime.now(UTC)
        user.token_version = getattr(user, "token_version", 1) + 1
        stmt = select(UserSession).where(
            UserSession.usuario_id == user.id,
            UserSession.revoked_at.is_(None),
        )
        res = await self.session.execute(stmt)
        for s in res.scalars().all():
            s.revoked_at = now

    async def create_user(self, actor: Usuario, payload: UserCreateRequest) -> UserResponse:
        """Create a user with role and scope validations."""
        is_actor_superadmin = actor.has_role(RolUsuario.SUPERADMIN.value)

        # Privilege escalation checks
        if RolUsuario.SUPERADMIN.value in payload.roles and not is_actor_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un SUPERADMIN puede asignar o crear usuarios con rol SUPERADMIN",
            )
        if RolUsuario.ADMIN.value in payload.roles and not is_actor_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un SUPERADMIN puede asignar o crear usuarios con rol ADMIN",
            )

        # Password confirmation check
        if payload.password != payload.password_confirmation:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La contraseña y su confirmación no coinciden",
            )
        if len(payload.password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La contraseña debe tener al menos 8 caracteres",
            )

        email_clean = payload.email.strip().lower()
        existing = await self.session.execute(select(Usuario).where(Usuario.email == email_clean))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El correo electrónico ya se encuentra registrado",
            )

        # Invariant: Líder o Usuario Adicional REQUIEREN campos organizacionales completos
        is_operational = any(
            r in [RolUsuario.LIDER_EQUIPO_EJECUTOR.value, RolUsuario.USUARIO_ADICIONAL.value]
            for r in payload.roles
        )
        if is_operational:
            if not payload.telefono or not payload.telefono.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El teléfono es obligatorio para usuarios operativos (Líder o Apoyo)",
                )
            if not payload.area or not payload.area.strip():
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="El área es obligatoria para usuarios operativos (Líder o Apoyo)",
                )
            if not payload.coordinacion_id or not payload.especialidad_id:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Líder y Usuario Adicional requieren asignación obligatoria de Coordinación y Especialidad",
                )

            # Check coordination exists and is active
            coord = await self.session.get(Coordinacion, payload.coordinacion_id)
            if coord is None or not coord.activo:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="La coordinación especificada no existe o se encuentra inactiva",
                )

            # Check specialty belongs to coordination and is active
            esp = await self.session.get(Especialidad, payload.especialidad_id)
            if esp is None or esp.coordinacion_id != payload.coordinacion_id or not esp.activo:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="La especialidad no existe, no pertenece a la coordinación o está inactiva",
                )

        new_user = Usuario(
            email=email_clean,
            hashed_password=hash_password(payload.password),
            nombre=payload.nombre.strip(),
            apellido=payload.apellido.strip(),
            telefono=payload.telefono.strip() if payload.telefono else None,
            area=payload.area.strip() if payload.area else None,
            coordinacion_id=payload.coordinacion_id,
            especialidad_id=payload.especialidad_id,
            estado=EstadoUsuario.ACTIVO,
            debe_cambiar_password=True,
            token_version=1,
        )
        self.session.add(new_user)
        await self.session.flush()

        if payload.roles:
            roles_stmt = select(Rol).where(Rol.nombre.in_(payload.roles))
            roles_res = await self.session.execute(roles_stmt)
            new_user.roles = list(roles_res.scalars().all())

        await self.audit_repo.add_event(
            entidad="Usuario",
            entidad_id=new_user.id,
            accion="USER_CREATED",
            detalle={"creado_por": str(actor.id), "email": new_user.email, "roles": payload.roles},
        )
        await self.session.commit()
        await self.session.refresh(new_user, attribute_names=["roles", "coordinacion", "especialidad"])
        return _map_user_response(new_user)

    async def get_user(self, actor: Usuario, user_id: uuid.UUID) -> UserResponse:
        """Fetch single user detail preventing unauthorized inspection of SUPERADMIN."""
        user = await self.session.get(
            Usuario,
            user_id,
            options=[
                selectinload(Usuario.roles),
                selectinload(Usuario.coordinacion),
                selectinload(Usuario.especialidad),
            ],
        )
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        # ADMIN cannot inspect or manage SUPERADMIN
        if user.has_role(RolUsuario.SUPERADMIN.value) and not actor.has_role(RolUsuario.SUPERADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Los administradores no tienen permisos para gestionar o inspeccionar a un SUPERADMIN",
            )

        return _map_user_response(user)

    async def list_users_paginated(
        self,
        actor: Usuario,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        role: str | None = None,
        estado: str | None = None,
        coordinacion_id: uuid.UUID | None = None,
        especialidad_id: uuid.UUID | None = None,
    ) -> PaginatedUsersResponse:
        """Paginated server-side user listing with filters."""
        if page < 1:
            page = 1
        if page_size < 1 or page_size > 100:
            page_size = 20

        stmt = select(Usuario).distinct()

        if role:
            stmt = stmt.join(UsuarioRol, UsuarioRol.usuario_id == Usuario.id).join(Rol, Rol.id == UsuarioRol.rol_id)
            stmt = stmt.where(Rol.nombre == role)

        if estado:
            stmt = stmt.where(Usuario.estado == estado)

        if coordinacion_id:
            stmt = stmt.where(Usuario.coordinacion_id == coordinacion_id)

        if especialidad_id:
            stmt = stmt.where(Usuario.especialidad_id == especialidad_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Usuario.nombre.ilike(term),
                    Usuario.apellido.ilike(term),
                    Usuario.email.ilike(term),
                    Usuario.area.ilike(term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total_res = await self.session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        # Fetch page items
        items_stmt = (
            stmt.options(
                selectinload(Usuario.roles),
                selectinload(Usuario.coordinacion),
                selectinload(Usuario.especialidad),
            )
            .order_by(Usuario.nombre, Usuario.apellido)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items_res = await self.session.execute(items_stmt)
        users = items_res.scalars().all()

        pages = math.ceil(total / page_size) if total > 0 else 1

        return PaginatedUsersResponse(
            items=[_map_user_response(u) for u in users],
            page=page,
            page_size=page_size,
            total=total,
            pages=pages,
        )

    async def update_user(self, actor: Usuario, user_id: uuid.UUID, payload: UserUpdateRequest) -> UserResponse:
        """Update user profile, organizational scope, and roles with strict consistency checks."""
        user = await self.session.get(
            Usuario,
            user_id,
            options=[
                selectinload(Usuario.roles),
                selectinload(Usuario.coordinacion),
                selectinload(Usuario.especialidad),
                selectinload(Usuario.equipos_liderados),
                selectinload(Usuario.membresias).selectinload(EquipoEjecutorMiembro.equipo),
            ],
        )
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        is_actor_superadmin = actor.has_role(RolUsuario.SUPERADMIN.value)

        # ADMIN cannot edit SUPERADMIN
        if user.has_role(RolUsuario.SUPERADMIN.value) and not is_actor_superadmin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un SUPERADMIN puede editar a otro SUPERADMIN",
            )

        # Role modifications check
        roles_changed = False
        if payload.roles is not None:
            if (
                RolUsuario.SUPERADMIN.value in payload.roles
                or RolUsuario.ADMIN.value in payload.roles
            ) and not is_actor_superadmin:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Solo un SUPERADMIN puede asignar o modificar los roles SUPERADMIN o ADMIN",
                )

            # Prevent removing SUPERADMIN role if it's the last active SUPERADMIN
            if user.has_role(RolUsuario.SUPERADMIN.value) and RolUsuario.SUPERADMIN.value not in payload.roles:
                active_superadmins = await self._count_active_superadmins()
                if active_superadmins <= 1:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="No es posible remover el rol SUPERADMIN al único SUPERADMIN activo del sistema",
                    )

            current_role_names = set(user.role_names)
            new_role_names = set(payload.roles)
            if current_role_names != new_role_names:
                roles_changed = True
                roles_stmt = select(Rol).where(Rol.nombre.in_(payload.roles))
                roles_res = await self.session.execute(roles_stmt)
                user.roles = list(roles_res.scalars().all())

        # Organizational scope changes check
        scope_changed = False
        new_coord_id = payload.coordinacion_id if payload.coordinacion_id is not None else user.coordinacion_id
        new_esp_id = payload.especialidad_id if payload.especialidad_id is not None else user.especialidad_id

        if payload.coordinacion_id is not None or payload.especialidad_id is not None:
            if new_coord_id != user.coordinacion_id or new_esp_id != user.especialidad_id:
                scope_changed = True

                # Validate specialty belongs to coordination
                if new_coord_id and new_esp_id:
                    esp = await self.session.get(Especialidad, new_esp_id)
                    if esp is None or esp.coordinacion_id != new_coord_id or not esp.activo:
                        raise HTTPException(
                            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                            detail="La nueva especialidad no pertenece a la coordinación o está inactiva",
                        )

                # Check inconsistencies with led teams
                for team in user.equipos_liderados:
                    if team.estado == EstadoEquipo.ACTIVO:
                        if team.coordinacion_id != new_coord_id or team.especialidad_id != new_esp_id:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"No se puede cambiar el ámbito organizacional: el usuario es líder del equipo activo '{team.nombre}' asignado a otra coordinación/especialidad",
                            )

                # Check inconsistencies with active memberships
                for membership in user.membresias:
                    if membership.activo and membership.equipo:
                        team = membership.equipo
                        if team.coordinacion_id != new_coord_id or team.especialidad_id != new_esp_id:
                            raise HTTPException(
                                status_code=status.HTTP_409_CONFLICT,
                                detail=f"No se puede cambiar el ámbito organizacional: el usuario es miembro activo del equipo '{team.nombre}' asignado a otra coordinación/especialidad",
                            )

                user.coordinacion_id = new_coord_id
                user.especialidad_id = new_esp_id

        # Update basic fields
        if payload.nombre is not None:
            user.nombre = payload.nombre.strip()
        if payload.apellido is not None:
            user.apellido = payload.apellido.strip()
        if payload.telefono is not None:
            user.telefono = payload.telefono.strip() if payload.telefono else None
        if payload.area is not None:
            user.area = payload.area.strip() if payload.area else None

        # Revocation rule: if roles or organizational scope change, revoke active sessions
        if roles_changed or scope_changed:
            await self._revoke_all_sessions(user)

        await self.audit_repo.add_event(
            entidad="Usuario",
            entidad_id=user.id,
            accion="USER_UPDATED" if not roles_changed else "USER_ROLES_CHANGED",
            detalle={
                "actualizado_por": str(actor.id),
                "roles_modificados": roles_changed,
                "scope_modificado": scope_changed,
            },
        )
        await self.session.commit()
        await self.session.refresh(user, attribute_names=["roles", "coordinacion", "especialidad"])
        return _map_user_response(user)

    async def change_user_status(
        self,
        actor: Usuario,
        user_id: uuid.UUID,
        payload: UserStatusUpdateRequest,
    ) -> UserResponse:
        """Change user status between ACTIVO, INACTIVO, and BLOQUEADO."""
        user = await self.session.get(Usuario, user_id, options=[selectinload(Usuario.roles)])
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        # Auto-lock / inactivate prevention
        if actor.id == user.id and payload.estado in [EstadoUsuario.INACTIVO.value, EstadoUsuario.BLOQUEADO.value]:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="No puede inactivar o bloquear su propia cuenta de usuario",
            )

        # ADMIN cannot block or inactivate SUPERADMIN
        if user.has_role(RolUsuario.SUPERADMIN.value) and not actor.has_role(RolUsuario.SUPERADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Los administradores no tienen permisos para cambiar el estado de un SUPERADMIN",
            )

        # Prevent inactivating or blocking the last active SUPERADMIN
        if (
            user.has_role(RolUsuario.SUPERADMIN.value)
            and user.estado == EstadoUsuario.ACTIVO
            and payload.estado != EstadoUsuario.ACTIVO.value
        ):
            active_superadmins = await self._count_active_superadmins()
            if active_superadmins <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="No es posible inactivar o bloquear al único SUPERADMIN activo del sistema",
                )

        try:
            nuevo_estado = EstadoUsuario(payload.estado)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Estado inválido: {payload.estado}. Opciones válidas: ACTIVO, INACTIVO, BLOQUEADO",
            )

        antiguo_estado = user.estado
        user.estado = nuevo_estado

        # Revocation rule: when transitioned to INACTIVO or BLOQUEADO, revoke all active sessions immediately
        if nuevo_estado in [EstadoUsuario.INACTIVO, EstadoUsuario.BLOQUEADO]:
            await self._revoke_all_sessions(user)

        await self.audit_repo.add_event(
            entidad="Usuario",
            entidad_id=user.id,
            accion="USER_STATUS_CHANGED",
            detalle={
                "cambiado_por": str(actor.id),
                "antiguo_estado": antiguo_estado.value if hasattr(antiguo_estado, "value") else str(antiguo_estado),
                "nuevo_estado": nuevo_estado.value,
            },
        )
        await self.session.commit()
        await self.session.refresh(user, attribute_names=["roles", "coordinacion", "especialidad"])
        return _map_user_response(user)

    async def reset_password(
        self,
        actor: Usuario,
        user_id: uuid.UUID,
        payload: UserResetPasswordRequest,
    ) -> dict[str, str]:
        """Admin resets user password with temporary flag, revoking all existing sessions."""
        user = await self.session.get(Usuario, user_id, options=[selectinload(Usuario.roles)])
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

        # ADMIN cannot reset SUPERADMIN password
        if user.has_role(RolUsuario.SUPERADMIN.value) and not actor.has_role(RolUsuario.SUPERADMIN.value):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un SUPERADMIN puede restablecer la contraseña de otro SUPERADMIN",
            )

        if payload.temporary_password != payload.confirm_temporary_password:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La contraseña temporal y su confirmación no coinciden",
            )

        if len(payload.temporary_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La contraseña temporal debe tener al menos 8 caracteres",
            )

        user.hashed_password = hash_password(payload.temporary_password)
        user.debe_cambiar_password = True
        await self._revoke_all_sessions(user)

        await self.audit_repo.add_event(
            entidad="Usuario",
            entidad_id=user.id,
            accion="USER_PASSWORD_RESET",
            detalle={"reseteado_por": str(actor.id), "debe_cambiar_password": True},
        )
        await self.session.commit()
        return {"message": "Contraseña temporal asignada exitosamente. Las sesiones activas han sido revocadas."}
