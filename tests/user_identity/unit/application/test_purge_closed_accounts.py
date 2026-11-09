from uuid import UUID

import pytest

from app.user_identity.application.exceptions import AccountNotFoundError
from tests.user_identity.unit.application.accounts_driver import AccountsDriver


async def _closed_and_blocked(driver: AccountsDriver) -> tuple[UUID, UUID]:
    """Luis's account closed (blocked 7 days ago) and Rosa's only blocked."""
    luis = await driver.register('luish')
    await driver.block(luis)
    driver.later(days=7)
    await driver.close_expired()
    rosa = await driver.register('rosaq')
    await driver.block(rosa)
    return luis, rosa


class TestPurgeClosedAccounts:
    async def test_deletes_the_closed_accounts(self) -> None:
        driver = AccountsDriver()
        luis, _ = await _closed_and_blocked(driver)

        deleted = await driver.purge()

        assert deleted == 1
        with pytest.raises(AccountNotFoundError):
            await driver.block(luis)

    async def test_keeps_the_blocked_accounts(self) -> None:
        driver = AccountsDriver()
        _, rosa = await _closed_and_blocked(driver)

        await driver.purge()

        assert (await driver.unblock(rosa))[0] == 'active'

    async def test_with_no_closed_account_deletes_nothing(self) -> None:
        driver = AccountsDriver()
        await driver.block(await driver.register('luish'))

        assert await driver.purge() == 0
