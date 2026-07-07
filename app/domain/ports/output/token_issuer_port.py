from abc import ABC, abstractmethod
from uuid import UUID


class TokenIssuerPort(ABC):
    @abstractmethod
    def issue(self, user_uuid: UUID) -> str:
        pass
