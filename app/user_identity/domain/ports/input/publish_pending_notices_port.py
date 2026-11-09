from abc import ABC, abstractmethod


class PublishPendingNoticesPort(ABC):
    @abstractmethod
    async def execute(self) -> tuple[int, int]:
        """Publishes every pending notice; returns how many were published and how
        many are still pending."""
