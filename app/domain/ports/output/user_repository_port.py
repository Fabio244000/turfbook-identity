from abc import ABC, abstractmethod

from app.domain.entities.user import User


class UserRepositoryPort(ABC):
    @abstractmethod
    def save(self, user: User) -> User: ...

    @abstractmethod
    def exists_by_username(self, username: str) -> bool: ...

    @abstractmethod
    def exists_by_email(self, email: str) -> bool: ...

    @abstractmethod
    def exists_by_cellphone(self, cellphone: str) -> bool: ...
