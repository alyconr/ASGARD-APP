"""Local development server launcher."""

from __future__ import annotations

import os
from pathlib import Path

from src.infrastructure.runtime import configure_asyncio_event_loop_policy

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000


def _get_bool_env(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default

    return value.strip().lower() not in {"0", "false", "no", "off"}


def _load_local_env_file() -> None:
    """Give backend/.env priority for the local development server."""
    env_path = BACKEND_ROOT / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        os.environ[key.strip()] = value.strip().strip("\"'")


def main() -> None:
    """Run uvicorn with Windows-compatible asyncio policy configured first."""
    _load_local_env_file()
    configure_asyncio_event_loop_policy()

    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=os.environ.get("BACKEND_DEV_HOST", DEFAULT_HOST),
        port=int(os.environ.get("BACKEND_DEV_PORT", str(DEFAULT_PORT))),
        reload=_get_bool_env("BACKEND_DEV_RELOAD", default=True),
    )


if __name__ == "__main__":
    main()
