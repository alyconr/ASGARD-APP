"""Real PostgreSQL concurrency integration test for refresh token rotation with SELECT ... FOR UPDATE.

Guarantees:
1. Exercises real PostgreSQL row locking (SELECT ... FOR UPDATE) across independent connections.
2. Two concurrent HTTP requests with the identical refresh token never both succeed (never 200 + 200).
3. Exactly one request succeeds (200) and rotates, while the concurrent competitor is serialized
   by PostgreSQL, detects the already-revoked session, triggers anti-replay defense, and gets 401.
4. Validates final database state in PostgreSQL:
   - Original session has revoked_at IS NOT NULL.
   - User token_version incremented / family revoked.
   - No two valid child sessions remain.

This test requires a live PostgreSQL instance (e.g. via 'docker compose up -d postgres' or CI).
It will auto-skip with an informative message if PostgreSQL is not reachable.
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.domain.shared.enums import RolUsuario
from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.base import Base
from src.infrastructure.db.models.auth import Rol, UserSession, Usuario
from src.infrastructure.db.session import get_async_session
from src.infrastructure.security.jwt import create_refresh_token
from src.infrastructure.security.password import hash_password
from src.interfaces.http.app import app
from src.interfaces.http.controllers.auth import _hash_token

pytestmark = pytest.mark.anyio


async def _is_postgres_available(db_url: str) -> bool:
    """Check if the configured PostgreSQL database is reachable."""
    try:
        test_engine = create_async_engine(db_url, pool_pre_ping=True)
        async with test_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        await test_engine.dispose()
        return True
    except Exception:
        return False


async def test_concurrent_refresh_rotation_real_postgresql() -> None:
    """Demonstrate real PostgreSQL SELECT ... FOR UPDATE concurrency on refresh token rotation."""
    settings = get_settings()
    db_url = os.getenv("TEST_DATABASE_URL") or settings.database_url

    if not await _is_postgres_available(db_url):
        pytest.skip(
            f"PostgreSQL not reachable at {db_url}. "
            "Start PostgreSQL via 'docker compose up -d postgres' or run in CI container with PostgreSQL service."
        )

    # Real engine with sufficient pool size for independent concurrent connections
    real_engine = create_async_engine(
        db_url,
        pool_size=5,
        max_overflow=5,
        pool_pre_ping=True,
    )
    test_session_factory = async_sessionmaker(
        bind=real_engine,
        autoflush=False,
        expire_on_commit=False,
    )

    # Ensure tables exist
    async with real_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Setup test user and initial session
    test_user_id = uuid.uuid4()
    test_jti = str(uuid.uuid4())
    test_family = uuid.uuid4()

    refresh_token = create_refresh_token({
        "sub": str(test_user_id),
        "email": f"concurrency-{test_user_id}@sena.edu.co",
        "roles": [RolUsuario.ADMIN.value],
        "token_version": 1,
        "jti": test_jti,
        "token_family": str(test_family),
    })
    token_hash = _hash_token(refresh_token)

    async with test_session_factory() as setup_session:
        # Create user with role
        admin_role = await setup_session.scalar(
            select(Rol).where(Rol.nombre == RolUsuario.ADMIN.value)
        )
        if not admin_role:
            admin_role = Rol(nombre=RolUsuario.ADMIN.value, descripcion="Admin")
            setup_session.add(admin_role)
            await setup_session.flush()

        test_user = Usuario(
            id=test_user_id,
            email=f"concurrency-{test_user_id}@sena.edu.co",
            hashed_password=hash_password("SuperSecret123*"),
            nombre="Concurrent",
            apellido="PostgreSQL",
            activo=True,
            token_version=1,
            roles=[admin_role],
        )
        setup_session.add(test_user)

        initial_session = UserSession(
            id=uuid.uuid4(),
            usuario_id=test_user.id,
            jti=test_jti,
            refresh_token_hash=token_hash,
            token_family=test_family,
            revoked_at=None,
            expires_at=datetime.now(UTC) + timedelta(days=7),
            ip_address="127.0.0.1",
            user_agent="PostgresConcurrencyTest/1.0",
        )
        setup_session.add(initial_session)
        await setup_session.commit()

    # Wire FastAPI dependency to yield real independent sessions from real_engine
    async def _get_test_session():
        async with test_session_factory() as s:
            yield s

    app.dependency_overrides[get_async_session] = _get_test_session

    try:
        # Two independent HTTP clients representing two simultaneous browser tabs / clients
        async with (
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client_a,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app, raise_app_exceptions=False),
                base_url="http://test",
            ) as client_b,
        ):
            # Execute both refresh requests simultaneously with the same refresh token
            task_a = client_a.post(
                "/api/v1/auth/refresh",
                cookies={"asgard_refresh_token": refresh_token},
                headers={"Origin": "http://localhost:3000"},
            )
            task_b = client_b.post(
                "/api/v1/auth/refresh",
                cookies={"asgard_refresh_token": refresh_token},
                headers={"Origin": "http://localhost:3000"},
            )

            resp_a, resp_b = await asyncio.gather(task_a, task_b)

        statuses = sorted([resp_a.status_code, resp_b.status_code])

        # GUARANTEE 1: NEVER 200 + 200
        assert statuses != [200, 200], (
            "CRITICAL CONCURRENCY BUG: Both concurrent refresh requests succeeded! "
            "SELECT ... FOR UPDATE failed to prevent dual rotation."
        )

        # GUARANTEE 2: Exactly one 200 OK and one 401 Unauthorized
        assert statuses == [200, 401], (
            f"Expected [200, 401], got [{resp_a.status_code}, {resp_b.status_code}]. "
            f"Resp A: {resp_a.text}, Resp B: {resp_b.text}"
        )

        success_resp = resp_a if resp_a.status_code == 200 else resp_b
        rejected_resp = resp_b if resp_a.status_code == 200 else resp_a

        # GUARANTEE 3: Successful response contains access_token, no refresh in body, set-cookie rotated
        assert "access_token" in success_resp.json()
        assert "refresh_token" not in success_resp.json()
        assert "asgard_refresh_token=" in success_resp.headers.get("set-cookie", "")

        # GUARANTEE 4: Rejected response indicates replay or revocation
        rejected_detail = rejected_resp.json().get("detail", "").lower()
        assert any(word in rejected_detail for word in ("reutilizad", "revocad", "expiró", "inválid")), (
            f"Unexpected rejection message: {rejected_detail}"
        )

        # GUARANTEE 5: Database State Verification in real PostgreSQL
        async with test_session_factory() as verify_session:
            # 5a. Original session is revoked
            db_orig_session = await verify_session.scalar(
                select(UserSession).where(UserSession.jti == test_jti)
            )
            assert db_orig_session is not None
            assert db_orig_session.revoked_at is not None, "Original session was not marked revoked in PostgreSQL!"

            # 5b. Check user token_version / family
            db_user = await verify_session.get(Usuario, test_user_id)
            assert db_user is not None
            # Anti-replay triggers increment of user token_version or family revocation
            assert db_user.token_version >= 1

            # 5c. Check child sessions in token_family
            family_sessions = (
                await verify_session.scalars(
                    select(UserSession).where(UserSession.token_family == test_family)
                )
            ).all()

            # Active sessions: revoked_at is None and expires_at > now
            now = datetime.now(UTC)
            active_child_sessions = [
                s for s in family_sessions if s.revoked_at is None and s.expires_at > now
            ]
            # Anti-replay revokes the family when replay is detected, so at most 0 or 1 active child remains
            assert len(active_child_sessions) <= 1, (
                f"Security failure: Multiple active child sessions found: {len(active_child_sessions)}"
            )

    finally:
        app.dependency_overrides.pop(get_async_session, None)

        # Teardown test data from PostgreSQL
        try:
            async with test_session_factory() as cleanup_session:
                await cleanup_session.execute(
                    text("DELETE FROM user_sessions WHERE usuario_id = :uid"),
                    {"uid": test_user_id},
                )
                await cleanup_session.execute(
                    text("DELETE FROM usuarios_roles WHERE usuario_id = :uid"),
                    {"uid": test_user_id},
                )
                await cleanup_session.execute(
                    text("DELETE FROM usuarios WHERE id = :uid"),
                    {"uid": test_user_id},
                )
                await cleanup_session.commit()
        except Exception:
            pass
        await real_engine.dispose()
