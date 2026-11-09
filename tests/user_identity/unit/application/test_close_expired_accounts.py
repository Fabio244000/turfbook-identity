import pytest

from app.user_identity.application.exceptions import AccountClosedError

# Raised by a use case written before 2026-11-09 (sign in): allowed while both coexist
# (reference/testing.md, "Use case tests").
from app.user_identity.domain.exceptions import InvalidCredentialsError
from tests.user_identity.unit.application.accounts_driver import AccountsDriver

CLOSED = (
    'Hola Luis, tu cuenta de TurfBook fue cerrada porque estuvo bloqueada 7 días sin que '
    'te comunicaras con TurfBook. Ya no podrás ingresar con ella. Si tienes dudas, '
    'comunícate con TurfBook al +51 999999998 o a turfbook@gmail.com.'
)


class TestCloseExpiredAccounts:
    async def test_closes_an_account_blocked_7_days_ago(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7)

        closed = await driver.close_expired()

        assert closed == 1

    async def test_does_not_close_it_a_moment_before_the_7_days(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7, seconds=-1)

        closed = await driver.close_expired()

        assert closed == 0

    async def test_closes_only_the_expired_accounts(self) -> None:
        driver = AccountsDriver()
        for username in ('luish', 'rosaq'):
            await driver.block(await driver.register(username))
        driver.later(days=4)
        ana = await driver.register('anap')
        await driver.block(ana)
        driver.later(days=3)

        closed = await driver.close_expired()

        assert closed == 2
        assert (await driver.unblock(ana))[0] == 'active'

    async def test_a_closed_account_cannot_sign_in(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7)

        await driver.close_expired()

        with pytest.raises(InvalidCredentialsError):
            await driver.sign_in('luish')

    async def test_a_closed_account_can_no_longer_be_unblocked(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7)

        await driver.close_expired()

        with pytest.raises(AccountClosedError):
            await driver.unblock(luis)

    async def test_tells_the_user_that_the_account_was_closed(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        await driver.block(luis)
        driver.later(days=7)

        await driver.close_expired()

        notice = driver.publisher.sent[-1]
        assert notice['recipient'] == luis
        assert notice['subject'] == 'Tu cuenta de TurfBook fue cerrada'
        assert notice['body'] == CLOSED


class TestCloseExpiredAccountsFailures:
    async def test_a_failed_publication_keeps_closing_the_others(self) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        rosa = await driver.register('rosaq', first_name='rosa')
        for account in (luis, rosa):
            await driver.block(account)
        driver.later(days=7)
        driver.publisher.failing_recipients = {luis}

        closed = await driver.close_expired()

        assert closed == 2
        assert driver.publisher.sent[-1]['recipient'] == rosa
        driver.publisher.failing_recipients = set()
        assert await driver.publish_pending() == (1, 0)

    async def test_a_failure_closing_one_account_keeps_the_ones_already_closed(
        self,
    ) -> None:
        driver = AccountsDriver()
        luis = await driver.register('luish')
        rosa = await driver.register('rosaq', first_name='rosa')
        for account in (luis, rosa):
            await driver.block(account)
        driver.later(days=7)
        driver.publisher.fails = True
        driver.uow.failing_commit = driver.uow.commits + 2

        with pytest.raises(RuntimeError):
            await driver.close_expired()

        driver.uow.failing_commit = None
        with pytest.raises(AccountClosedError):
            await driver.unblock(luis)
        assert await driver.close_expired() == 1
