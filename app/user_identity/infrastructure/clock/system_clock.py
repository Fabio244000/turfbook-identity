from datetime import UTC, datetime

from app.user_identity.domain.ports.driven.clock_port import ClockPort


class SystemClock(ClockPort):
    def now(self) -> datetime:
        return datetime.now(UTC)
