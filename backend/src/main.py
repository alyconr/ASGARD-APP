"""ASGI entrypoint for the backend application."""

from src.interfaces.http.app import app

__all__ = ["app"]
