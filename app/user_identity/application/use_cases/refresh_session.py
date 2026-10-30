from datetime import timedelta

from app.user_identity.application.sessions import issue_refresh_token, revoke_session
from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.entities.session_tokens import SessionTokens
from app.user_identity.domain.exceptions import InvalidRefreshTokenError
from app.user_identity.domain.ports.input.refresh_session_port import (
    RefreshSessionPort,
)
from app.user_identity.domain.ports.output.clock_port import ClockPort
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.token_issuer_port import TokenIssuerPort
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


class RefreshSessionUseCase(RefreshSessionPort):
    def __init__(
        self,
        uow: UnitOfWorkPort,
        token_issuer: TokenIssuerPort,
        clock: ClockPort,
        refresh_token_generator: RefreshTokenGeneratorPort,
        refresh_token_ttl: timedelta,
    ) -> None:
        self._uow = uow
        self._token_issuer = token_issuer
        self._clock = clock
        self._refresh_token_generator = refresh_token_generator
        self._refresh_token_ttl = refresh_token_ttl

    async def execute(self, refresh_token: str) -> SessionTokens:
        now = self._clock.now()
        async with self._uow:
            token = await self._find(refresh_token)
            if token.was_used:
                # A reused token is a theft signal: the revocation is committed
                # before the error, so it survives the rollback.
                await revoke_session(self._uow, token.session_uuid, now)
                await self._uow.commit()
                raise InvalidRefreshTokenError()
            token.use(now)
            if not await self._uow.users.exists_by_uuid(token.user_uuid):
                raise InvalidRefreshTokenError()
            await self._uow.refresh_tokens.update(token)
            new_refresh_token = await issue_refresh_token(
                self._uow,
                self._refresh_token_generator,
                user_uuid=token.user_uuid,
                session_uuid=token.session_uuid,
                now=now,
                ttl=self._refresh_token_ttl,
            )
            await self._uow.commit()
        access_token = self._token_issuer.issue(token.user_uuid)
        return SessionTokens(access_token, new_refresh_token)

    async def _find(self, refresh_token: str) -> RefreshToken:
        token_hash = self._refresh_token_generator.hash(refresh_token)
        token = await self._uow.refresh_tokens.get_by_hash(token_hash)
        if token is None:
            raise InvalidRefreshTokenError()
        return token
