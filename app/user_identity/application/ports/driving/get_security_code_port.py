from abc import ABC, abstractmethod

from app.user_identity.application.dtos.outputs import SupportSecurityCode


class GetSecurityCodePort(ABC):
    @abstractmethod
    async def execute(self, cellphone: str, process_type: str) -> SupportSecurityCode:
        """Support gets the code in force of the user's process in progress, or
        generates one that is never sent to the user.

        Raises UserNotFoundError, NoProcessInProgressError, SupportCodeLimitError,
        SecurityCodeDeliveredError or SupportProcessValidatedError."""
