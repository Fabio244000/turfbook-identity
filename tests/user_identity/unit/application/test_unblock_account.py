from datetime import timedelta
from uuid import uuid4

import pytest

from app.user_identity.application.exceptions import (
    AccountClosedError,
    AccountNotBlockedError,
    AccountNotFoundError,
)

# Raised by a use case written before 2026-11-09 (sign in): allowed while both coexist
# (reference/testing.md, "Use case tests").
from app.user_identity.domain.exceptions import InvalidCredentialsError
from tests.user_identity.unit.application.accounts_driver import (
    NOW,
    PASSWORD,
    AccountsDriver,
)

UNBLOCKED = (
    'Hola Luis, tu cuenta de TurfBook fue desbloqueada. Ya puedes ingresar con tu '
    'usuario y contraseña. Si tienes dudas, comunícate con TurfBook al +51 999999998 o '
    'a turfbook@gmail.com.'
)


async def _fail_sign_in(driver: AccountsDriver, times: int) -> None:
    for _ in range(times):
        with pytest.raises(InvalidCredentialsError):
            await driver.sign_in('luish', password=f'not-{PASSWORD}')


class TestUnblockAccount:
    async def test_unblocks_a_blocked_account(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=2)

        result = await driver.unblock(luis)

        assert result == ('active', NOW + timedelta(days=2))

    async def test_the_user_signs_in_again(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)

        await driver.unblock(luis)

        assert await driver.sign_in('luish')

    async def test_the_failed_attempts_start_again_from_zero(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await _fail_sign_in(driver, times=4)
        await driver.block(luis)

        await driver.unblock(luis)

        await _fail_sign_in(driver, times=4)
        assert await driver.sign_in('luish')

    async def test_the_account_is_no_longer_counted_for_closing(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)

        await driver.unblock(luis)

        driver.later(days=7)
        assert await driver.close_expired() == 0

    async def test_tells_the_user_that_the_account_was_unblocked(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)

        await driver.unblock(luis)

        notice = driver.publisher.sent[-1]
        assert notice['recipient'] == luis
        assert notice['subject'] == 'Tu cuenta de TurfBook fue desbloqueada'
        assert notice['body'] == UNBLOCKED


class TestUnblockAccountRejections:
    async def test_rejects_an_account_that_does_not_exist(self) -> None:
        driver = AccountsDriver()

        with pytest.raises(AccountNotFoundError, match='^The account does not exist.$'):
            await driver.unblock(uuid4())

    async def test_rejects_an_account_that_is_not_blocked(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')

        with pytest.raises(
            AccountNotBlockedError, match='^The account is not blocked.$'
        ):
            await driver.unblock(luis)

    async def test_rejects_a_closed_account(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7)
        await driver.close_expired()

        with pytest.raises(
            AccountClosedError, match='^The account is closed and cannot be changed.$'
        ):
            await driver.unblock(luis)

    async def test_a_failed_publication_keeps_the_account_active(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.publisher.fails = True

        result = await driver.unblock(luis)

        assert result[0] == 'active'
        assert await driver.sign_in('luish')
