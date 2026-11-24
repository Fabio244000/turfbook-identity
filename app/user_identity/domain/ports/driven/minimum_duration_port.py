from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager


class MinimumDurationPort(ABC):
    @abstractmethod
    def at_least(self, seconds: float) -> AbstractAsyncContextManager[None]:
        """Wraps an operation so it lasts at least `seconds`, also when it fails: its
        duration reveals nothing about what happened inside."""
