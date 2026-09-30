"""Decoupled domain notification events and hooks for pedagogical review & RA locking."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Canonical notification event names (Section 21)
EVENT_EDIT_REQUEST_CREATED = "edit_request.created"
EVENT_EDIT_REQUEST_APPROVED = "edit_request.approved"
EVENT_EDIT_REQUEST_PARTIALLY_APPROVED = "edit_request.partially_approved"
EVENT_EDIT_REQUEST_REJECTED = "edit_request.rejected"
EVENT_PLANNING_RESUBMITTED = "planning.resubmitted"
EVENT_PLANNING_REAPPROVED = "planning.reapproved"

ALL_NOTIFICATION_EVENTS: tuple[str, ...] = (
    EVENT_EDIT_REQUEST_CREATED,
    EVENT_EDIT_REQUEST_APPROVED,
    EVENT_EDIT_REQUEST_PARTIALLY_APPROVED,
    EVENT_EDIT_REQUEST_REJECTED,
    EVENT_PLANNING_RESUBMITTED,
    EVENT_PLANNING_REAPPROVED,
)


@dataclass(frozen=True)
class DomainNotificationEvent:
    """Immutable domain notification event payload ready for external adapters (e.g. Resend)."""

    event_name: str
    entity_id: uuid.UUID
    actor_id: uuid.UUID | None
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def event_type(self) -> str:
        return self.event_name


NotificationHandler = Callable[[DomainNotificationEvent], Awaitable[None] | None]


class NotificationEventDispatcher:
    """In-process domain event bus decoupled from specific email/push providers."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[NotificationHandler]] = {}
        self._history: list[DomainNotificationEvent] = []

    def subscribe(self, event_name: str, handler: NotificationHandler) -> None:
        """Register a hook/listener for a specific event name or '*' for all events."""
        self._handlers.setdefault(event_name, []).append(handler)

    def clear_history(self) -> None:
        """Clear recorded events (useful for test assertions)."""
        self._history.clear()

    def clear_recent_events(self) -> None:
        """Alias for clear_history."""
        self._history.clear()

    def get_recent_events(self) -> list[DomainNotificationEvent]:
        """Return emitted events in chronological order."""
        return list(self._history)

    @property
    def history(self) -> list[DomainNotificationEvent]:
        """Return emitted events in chronological order."""
        return list(self._history)

    def emit(
        self,
        event_name: str | None = None,
        entity_id: uuid.UUID | None = None,
        *,
        event_type: str | None = None,
        actor_id: uuid.UUID | None = None,
        recipient_ids: list[uuid.UUID] | None = None,
        referencia_id: uuid.UUID | None = None,
        planning_id: uuid.UUID | None = None,
        request_id: uuid.UUID | None = None,
        team_id: uuid.UUID | None = None,
        payload: dict[str, Any] | None = None,
    ) -> DomainNotificationEvent:
        """Emit a domain notification event and invoke registered hooks safely."""
        resolved_name = event_name or event_type or "domain.event"
        resolved_entity = (
            entity_id
            or request_id
            or planning_id
            or referencia_id
            or team_id
            or uuid.uuid4()
        )
        merged_payload = dict(payload or {})
        if recipient_ids:
            merged_payload["recipient_ids"] = [str(r) for r in recipient_ids]
        if referencia_id:
            merged_payload["referencia_id"] = str(referencia_id)
        if planning_id:
            merged_payload["planning_id"] = str(planning_id)
        if request_id:
            merged_payload["request_id"] = str(request_id)
        if team_id:
            merged_payload["team_id"] = str(team_id)

        event = DomainNotificationEvent(
            event_name=resolved_name,
            entity_id=resolved_entity,
            actor_id=actor_id,
            payload=merged_payload,
        )
        self._history.append(event)
        logger.info(
            "Domain notification event emitted: %s (entity=%s, actor=%s)",
            resolved_name,
            resolved_entity,
            actor_id,
        )

        handlers = [
            *self._handlers.get(resolved_name, []),
            *self._handlers.get("*", []),
        ]
        for handler in handlers:
            try:
                handler(event)
            except Exception:
                logger.exception(
                    "Error in notification hook for event %s", resolved_name
                )
        return event


# Shared singleton dispatcher
notification_dispatcher = NotificationEventDispatcher()
