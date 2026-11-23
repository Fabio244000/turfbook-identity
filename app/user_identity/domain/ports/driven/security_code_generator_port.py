from abc import ABC, abstractmethod


class SecurityCodeGeneratorPort(ABC):
    @abstractmethod
    def generate(self) -> str:
        """A new security code of six random digits."""
