"""Query service for institutional audit viewer with sensitive field redaction."""

from __future__ import annotations

import math
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.application.dto.audit_admin import (
    ActorSummaryDTO,
    AuditFilterDTO,
    AuditItemDTO,
    AuditPaginatedResponseDTO,
)
from src.infrastructure.db.models.audit import EventoAuditoria

SENSITIVE_PATTERNS = (
    "password",
    "token",
    "secret",
    "cookie",
    "authorization",
    "key",
    "credencial",
)


def sanitize_audit_payload(value: Any) -> Any:
    """Recursively redacts sensitive keys such as passwords, tokens, and secrets."""
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for k, v in value.items():
            k_lower = str(k).lower()
            if any(pattern in k_lower for pattern in SENSITIVE_PATTERNS):
                sanitized[k] = "[REDACTED]"
            else:
                sanitized[k] = sanitize_audit_payload(v)
        return sanitized
    if isinstance(value, list):
        return [sanitize_audit_payload(item) for item in value]
    return value


class AuditQueryService:
    """Read-only service for querying and sanitizing audit logs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_events_paginated(self, filters: AuditFilterDTO) -> AuditPaginatedResponseDTO:
        """Query audit records with pagination, filtering, and sanitization."""
        query = select(EventoAuditoria).options(selectinload(EventoAuditoria.actor))
        count_query = select(func.count(EventoAuditoria.id))

        conditions = []
        if filters.fecha_desde:
            conditions.append(EventoAuditoria.fecha_evento >= filters.fecha_desde)
        if filters.fecha_hasta:
            conditions.append(EventoAuditoria.fecha_evento <= filters.fecha_hasta)
        if filters.actor_usuario_id:
            conditions.append(EventoAuditoria.actor_usuario_id == filters.actor_usuario_id)
        if filters.accion:
            conditions.append(EventoAuditoria.accion == filters.accion.strip())
        if filters.entidad:
            conditions.append(EventoAuditoria.entidad == filters.entidad.strip())
        if filters.referencia_id:
            conditions.append(EventoAuditoria.referencia_id == filters.referencia_id)
        if filters.search and filters.search.strip():
            term = f"%{filters.search.strip()}%"
            conditions.append(
                or_(
                    EventoAuditoria.accion.ilike(term),
                    EventoAuditoria.entidad.ilike(term),
                )
            )

        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one() or 0
        total_pages = math.ceil(total / filters.page_size) if filters.page_size > 0 else 1

        offset = max(0, (filters.page - 1) * filters.page_size)
        query = query.order_by(EventoAuditoria.fecha_evento.desc()).offset(offset).limit(filters.page_size)

        res = await self.session.execute(query)
        rows = res.scalars().all()

        def extract_actor_dto(actor: Any) -> ActorSummaryDTO | None:
            if not actor:
                return None
            rol_name = ""
            if hasattr(actor, "role_names") and actor.role_names:
                rol_name = next(iter(actor.role_names))
            elif hasattr(actor, "roles") and actor.roles:
                first_rol = actor.roles[0]
                rol_name = getattr(first_rol, "nombre", str(first_rol))
            elif hasattr(actor, "rol") and actor.rol:
                rol_name = getattr(actor.rol, "value", str(actor.rol))

            return ActorSummaryDTO(
                id=actor.id,
                nombre=actor.nombre,
                apellido=actor.apellido,
                email=actor.email,
                rol=rol_name,
            )

        items: list[AuditItemDTO] = []
        for row in rows:
            actor_dto = extract_actor_dto(row.actor)
            sanitized_detail = sanitize_audit_payload(row.detalle) if row.detalle is not None else None

            items.append(
                AuditItemDTO(
                    id=row.id,
                    fecha_evento=row.fecha_evento,
                    accion=row.accion,
                    entidad=row.entidad,
                    entidad_id=row.entidad_id,
                    actor=actor_dto,
                    referencia_id=row.referencia_id,
                    detalle=sanitized_detail,
                )
            )

        return AuditPaginatedResponseDTO(
            items=items,
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=total_pages,
        )

    async def get_event_by_id(self, event_id: UUID) -> AuditItemDTO | None:
        """Fetch a single audit event by ID with redacted sensitive payload."""
        stmt = (
            select(EventoAuditoria)
            .options(selectinload(EventoAuditoria.actor))
            .where(EventoAuditoria.id == event_id)
        )
        res = await self.session.execute(stmt)
        row = res.scalar_one_or_none()
        if not row:
            return None

        actor_dto: ActorSummaryDTO | None = None
        if row.actor:
            rol_name = ""
            if hasattr(row.actor, "role_names") and row.actor.role_names:
                rol_name = next(iter(row.actor.role_names))
            elif hasattr(row.actor, "roles") and row.actor.roles:
                first_rol = row.actor.roles[0]
                rol_name = getattr(first_rol, "nombre", str(first_rol))
            elif hasattr(row.actor, "rol") and row.actor.rol:
                rol_name = getattr(row.actor.rol, "value", str(row.actor.rol))

            actor_dto = ActorSummaryDTO(
                id=row.actor.id,
                nombre=row.actor.nombre,
                apellido=row.actor.apellido,
                email=row.actor.email,
                rol=rol_name,
            )

        sanitized_detail = sanitize_audit_payload(row.detalle) if row.detalle is not None else None

        return AuditItemDTO(
            id=row.id,
            fecha_evento=row.fecha_evento,
            accion=row.accion,
            entidad=row.entidad,
            entidad_id=row.entidad_id,
            actor=actor_dto,
            referencia_id=row.referencia_id,
            detalle=sanitized_detail,
        )
