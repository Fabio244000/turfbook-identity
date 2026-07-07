from abc import ABC, abstractmethod

from app.domain.entities.user import User


class RegisterUserPort(ABC):
    @abstractmethod
    def execute(
        self,
        first_name: str,
        last_name: str,
        cellphone: str,
        username: str | None = None,
        password: str | None = None,
        email: str | None = None,
    ) -> tuple[User, bool]: ...
