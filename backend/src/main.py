"""ASGI entrypoint for the backend application."""

from src.infrastructure.runtime import configure_asyncio_event_loop_policy

configure_asyncio_event_loop_policy()

from src.interfaces.http.app import app

__all__ = ["app"]
