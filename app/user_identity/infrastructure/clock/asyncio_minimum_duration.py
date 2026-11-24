import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.user_identity.domain.ports.driven.minimum_duration_port import (
    MinimumDurationPort,
)


class AsyncioMinimumDuration(MinimumDurationPort):
    """Measures with the monotonic clock (it never jumps) and sleeps what is left."""

    @asynccontextmanager
    async def at_least(self, seconds: float) -> AsyncIterator[None]:
        started = time.monotonic()
        try:
            yield
        finally:
            left = seconds - (time.monotonic() - started)
            if left > 0:
                await asyncio.sleep(left)
