from abc import ABC, abstractmethod


class PasswordHasherPort(ABC):
    @abstractmethod
    def hash(self, password: str) -> str: ...

    @abstractmethod
    def verify(self, password: str, hashed: str | None) -> bool:
        """Without a hash (no such user, or no password) it still takes the time of
        a real verification and returns False, so the answer time reveals nothing."""
