"""Runtime compatibility helpers for local and deployed backend processes."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from typing import cast


def configure_asyncio_event_loop_policy() -> None:
    """Use an event-loop policy compatible with psycopg async on Windows."""
    if sys.platform != "win32":
        return

    current_policy = asyncio.get_event_loop_policy()
    if current_policy.__class__.__name__ == "WindowsSelectorEventLoopPolicy":
        return

    selector_policy_factory = getattr(
        asyncio,
        "WindowsSelectorEventLoopPolicy",
        None,
    )
    if selector_policy_factory is None:
        return

    policy_factory = cast(
        Callable[[], asyncio.AbstractEventLoopPolicy],
        selector_policy_factory,
    )
    asyncio.set_event_loop_policy(policy_factory())
