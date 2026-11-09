from uuid import uuid4

import pytest

from app.user_identity.application.exceptions import (
    AccountAlreadyBlockedError,
    AccountClosedError,
    AccountNotFoundError,
)

# Raised by use cases written before 2026-11-09 (sign in, renew): allowed while both
# coexist (reference/testing.md, "Use case tests").
from app.user_identity.domain.exceptions import (
    AccountBlockedError,
    InvalidRefreshTokenError,
)
from tests.user_identity.unit.application.accounts_driver import NOW, AccountsDriver

BLOCKED_BY_TURFBOOK = (
    'Hola Luis, TurfBook bloqueó tu cuenta. Comunícate con TurfBook al +51 999999998 o a '
    'turfbook@gmail.com dentro de los próximos 7 días; si no, tu cuenta se cerrará.'
)


class TestBlockAccount:
    async def test_blocks_an_active_account(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')

        result = await driver.block(luis)

        assert result == ('blocked', NOW)

    async def test_a_blocked_account_cannot_sign_in(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')

        await driver.block(luis)

        with pytest.raises(AccountBlockedError):
            await driver.sign_in('luish')

    async def test_ends_the_open_sessions_of_the_account(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        session = await driver.sign_in('luish')

        await driver.block(luis)

        await driver.unblock(luis)
        with pytest.raises(InvalidRefreshTokenError):
            await driver.refresh(session)

    async def test_tells_the_user_that_turfbook_blocked_the_account(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')

        await driver.block(luis)

        [notice] = driver.publisher.sent
        assert notice['recipient'] == luis
        assert notice['subject'] == 'Tu cuenta de TurfBook fue bloqueada'
        assert notice['body'] == BLOCKED_BY_TURFBOOK


class TestBlockAccountRejections:
    async def test_rejects_an_account_that_does_not_exist(self) -> None:
        driver = AccountsDriver()

        with pytest.raises(AccountNotFoundError, match='^The account does not exist.$'):
            await driver.block(uuid4())

    async def test_rejects_an_account_already_blocked(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)

        with pytest.raises(
            AccountAlreadyBlockedError, match='^The account is already blocked.$'
        ):
            await driver.block(luis)

    async def test_blocking_again_does_not_restart_the_days_before_closing(
        self,
    ) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=3)
        with pytest.raises(AccountAlreadyBlockedError):
            await driver.block(luis)
        driver.later(days=4)

        closed = await driver.close_expired()

        assert closed == 1

    async def test_rejects_a_closed_account(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7)
        await driver.close_expired()

        with pytest.raises(
            AccountClosedError, match='^The account is closed and cannot be changed.$'
        ):
            await driver.block(luis)


class TestBlockAccountNotice:
    async def test_a_failed_publication_keeps_the_block_and_the_notice_pending(
        self,
    ) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        driver.publisher.fails = True

        result = await driver.block(luis)

        assert result == ('blocked', NOW)
        driver.publisher.fails = False
        assert await driver.publish_pending() == (1, 0)
        [notice] = driver.publisher.sent
        assert notice['body'] == BLOCKED_BY_TURFBOOK
