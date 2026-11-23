from abc import ABC, abstractmethod

from app.user_identity.domain.entities.notice import Notice


class NoticePublisherPort(ABC):
    @abstractmethod
    async def publish(self, notice: Notice) -> None:
        """Raises NoticeNotPublishedError when the notice could not be published."""
