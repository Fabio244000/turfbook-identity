"""Session steps shared by several use cases. They work inside the caller's Unit of
Work and never commit: committing stays in the use case."""

from datetime import datetime, timedelta
from uuid import UUID

from app.user_identity.domain.entities.refresh_token import RefreshToken
from app.user_identity.domain.ports.output.refresh_token_generator_port import (
    RefreshTokenGeneratorPort,
)
from app.user_identity.domain.ports.output.unit_of_work_port import UnitOfWorkPort


async def issue_refresh_token(
    uow: UnitOfWorkPort,
    generator: RefreshTokenGeneratorPort,
    user_uuid: UUID,
    session_uuid: UUID,
    now: datetime,
    ttl: timedelta,
) -> str:
    """Adds a new refresh token to the session and returns its value; only the hash
    is stored."""
    refresh_token = generator.generate()
    await uow.refresh_tokens.add(
        RefreshToken.issue(
            user_uuid=user_uuid,
            session_uuid=session_uuid,
            token_hash=generator.hash(refresh_token),
            now=now,
            ttl=ttl,
        )
    )
    return refresh_token


async def revoke_session(
    uow: UnitOfWorkPort, session_uuid: UUID, now: datetime
) -> None:
    for token in await uow.refresh_tokens.get_by_session(session_uuid):
        token.revoke(now)
        await uow.refresh_tokens.update(token)
