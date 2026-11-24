import asyncio
import time

import pytest

from app.user_identity.infrastructure.clock.asyncio_minimum_duration import (
    AsyncioMinimumDuration,
)

FLOOR = 0.2


class TestAsyncioMinimumDuration:
    async def test_a_quick_operation_lasts_the_floor(self) -> None:
        started = time.monotonic()

        async with AsyncioMinimumDuration().at_least(FLOOR):
            pass

        assert time.monotonic() - started >= FLOOR

    async def test_a_failed_operation_lasts_the_floor_too(self) -> None:
        started = time.monotonic()

        with pytest.raises(ValueError, match='^boom$'):
            async with AsyncioMinimumDuration().at_least(FLOOR):
                raise ValueError('boom')

        assert time.monotonic() - started >= FLOOR

    async def test_a_slow_operation_is_not_made_longer(self) -> None:
        started = time.monotonic()

        async with AsyncioMinimumDuration().at_least(FLOOR):
            await asyncio.sleep(FLOOR * 2)

        # Waiting the floor again after it would end past 3 floors.
        assert time.monotonic() - started < FLOOR * 2.5
