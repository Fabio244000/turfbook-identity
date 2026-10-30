from app.user_identity.application.sessions import revoke_session
from app.user_identity.domain.ports.input.revoke_session_port import RevokeSessionPort
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class RevokeSessionUseCase(RevokeSessionPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        clock: ClockPort,
        refresh_token_generator: RefreshTokenGeneratorPort,
    ) -> None:
        self._uow = uow
        self._clock = clock
        self._refresh_token_generator = refresh_token_generator

    async def execute(self, refresh_token: str) -> None:
        """Idempotent: an unknown or already revoked token is not an error."""
        now = self._clock.now()
        token_hash = self._refresh_token_generator.hash(refresh_token)
        async with self._uow:
            token = await self._uow.refresh_tokens.get_by_hash(token_hash)
            if token is None:
                return
            await revoke_session(self._uow, token.session_uuid, now)
            await self._uow.commit()
