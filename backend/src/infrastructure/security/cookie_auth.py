"""Centralized cookie and CSRF origin verification helpers."""

from __future__ import annotations

from urllib.parse import urlparse
from fastapi import HTTPException, Request, Response, status

from src.infrastructure.config.settings import get_settings


def set_auth_refresh_cookie(response: Response, refresh_token: str) -> None:
    """Set the HttpOnly refresh token cookie according to active environment policy."""
    settings = get_settings()
    cookie_kwargs: dict[str, object] = {
        "key": settings.auth_cookie_name,
        "value": refresh_token,
        "httponly": True,
        "secure": settings.effective_cookie_secure,
        "samesite": settings.auth_cookie_samesite.lower(),
        "max_age": settings.jwt_refresh_token_expire_days * 86400,
        "path": settings.auth_cookie_path,
    }
    if settings.auth_cookie_domain:
        cookie_kwargs["domain"] = settings.auth_cookie_domain

    response.set_cookie(**cookie_kwargs)


def clear_auth_refresh_cookie(response: Response) -> None:
    """Clear the HttpOnly refresh token cookie."""
    settings = get_settings()
    delete_kwargs: dict[str, object] = {
        "key": settings.auth_cookie_name,
        "path": settings.auth_cookie_path,
    }
    if settings.auth_cookie_domain:
        delete_kwargs["domain"] = settings.auth_cookie_domain

    response.delete_cookie(**delete_kwargs)


def normalize_origin(origin_or_url: str | None) -> str | None:
    """Extract standard scheme://host[:port] representation from an origin or referer."""
    if not origin_or_url:
        return None
    parsed = urlparse(origin_or_url)
    if not parsed.scheme or not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


async def verify_csrf_origin(request: Request) -> None:
    """Validate request Origin/Referer against allowed CORS origins for cookie-authenticated requests."""
    settings = get_settings()
    origin_header = request.headers.get("origin")
    referer_header = request.headers.get("referer")

    incoming_origin = normalize_origin(origin_header) or normalize_origin(referer_header)
    allowed_origins = {normalize_origin(o) for o in settings.cors_allow_origin_list if normalize_origin(o)}

    cookie_present = settings.auth_cookie_name in request.cookies

    # If an origin was explicitly provided, it MUST belong to the trusted set
    if incoming_origin is not None:
        if incoming_origin not in allowed_origins:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origen no permitido para esta operación (CSRF protection)",
            )
        return

    # In production/staging, requests authenticated via cookie MUST provide an Origin or Referer
    if cookie_present and settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origen o Referer obligatorio para operaciones basadas en sesión",
        )
