from abc import ABC, abstractmethod


class RefreshTokenGeneratorPort(ABC):
    @abstractmethod
    def generate(self) -> str: ...

    @abstractmethod
    def hash(self, token: str) -> str: ...
