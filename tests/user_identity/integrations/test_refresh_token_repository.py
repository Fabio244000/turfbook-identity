from datetime import timedelta

from app.user_identity.infrastructure.database.repositories.refresh_token_repository import (
    RefreshTokenRepository,
)
from tests.user_identity.integrations.conftest import REFRESH_TOKEN_TTL, REGISTERED_AT

LATER = REGISTERED_AT + timedelta(hours=1)


class TestRefreshTokenRepository:
    async def test_adds_a_refresh_token(
        self, session, existing_user, new_refresh_token, stored_refresh_token
    ):
        token = new_refresh_token(existing_user)

        await RefreshTokenRepository(session).add(token)
        await session.commit()

        assert await stored_refresh_token(token.uuid) == (
            existing_user.uuid,
            token.session_uuid,
            token.token_hash,
            REGISTERED_AT,
            REGISTERED_AT + REFRESH_TOKEN_TTL,
            None,
            None,
        )

    async def test_finds_a_token_by_its_hash(
        self, session, existing_user, new_refresh_token, insert_refresh_token
    ):
        token = new_refresh_token(existing_user)
        await insert_refresh_token(token)

        found = await RefreshTokenRepository(session).get_by_hash(token.token_hash)

        assert found == token

    async def test_does_not_find_a_hash_nobody_has(
        self, session, new_user, new_refresh_token
    ):
        unknown = new_refresh_token(new_user())

        found = await RefreshTokenRepository(session).get_by_hash(unknown.token_hash)

        assert found is None

    async def test_finds_every_token_of_a_session_and_no_other(
        self, session, existing_user, new_refresh_token, insert_refresh_token
    ):
        first = new_refresh_token(existing_user)
        second = new_refresh_token(existing_user, session_uuid=first.session_uuid)
        other_session = new_refresh_token(existing_user)
        for token in (first, second, other_session):
            await insert_refresh_token(token)

        found = await RefreshTokenRepository(session).get_by_session(first.session_uuid)

        assert {token.uuid for token in found} == {first.uuid, second.uuid}

    async def test_saves_the_changes_of_a_token(
        self,
        session,
        existing_user,
        new_refresh_token,
        insert_refresh_token,
        stored_refresh_token,
    ):
        token = new_refresh_token(existing_user)
        await insert_refresh_token(token)
        token.use(LATER)
        token.revoke(LATER)

        await RefreshTokenRepository(session).update(token)
        await session.commit()

        stored = await stored_refresh_token(token.uuid)
        assert stored is not None
        assert stored[5:] == (LATER, LATER)
