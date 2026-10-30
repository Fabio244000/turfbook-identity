from abc import ABC, abstractmethod


class RevokeSessionPort(ABC):
    @abstractmethod
    async def execute(self, refresh_token: str) -> None: ...
