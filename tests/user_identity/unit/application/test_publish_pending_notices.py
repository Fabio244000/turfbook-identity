import pytest

# Raised by a use case written before 2026-11-09 (sign in): allowed while both coexist
# (reference/testing.md, "Use case tests").
from app.user_identity.domain.exceptions import InvalidCredentialsError
from tests.user_identity.unit.application.accounts_driver import (
    PASSWORD,
    AccountsDriver,
)


class TestPublishPendingNotices:
    async def test_publishes_every_pending_notice_once(self) -> None:
        driver = AccountsDriver()
        driver.publisher.fails = True
        for username in ('luish', 'rosaq'):
            await driver.block(await driver.register(username))
        driver.publisher.fails = False

        first_run = await driver.publish_pending()
        second_run = await driver.publish_pending()

        assert (first_run, second_run) == ((2, 0), (0, 0))
        assert len(driver.publisher.sent) == 2

    async def test_publishes_a_pending_notice_with_its_same_notice_id(self) -> None:
        driver = AccountsDriver()
        driver.publisher.fails = True
        await driver.block(await driver.register('luish'))
        [failed_id] = driver.publisher.attempted_ids
        driver.publisher.fails = False

        await driver.publish_pending()

        [notice] = driver.publisher.sent
        assert notice['notice_id'] == failed_id

    async def test_a_notice_that_fails_again_stays_pending_and_the_rest_go_out(
        self,
    ) -> None:
        driver = AccountsDriver()
        driver.publisher.fails = True
        luis = await driver.register('luish')
        rosa = await driver.register('rosaq')
        for account in (luis, rosa):
            await driver.block(account)
        driver.publisher.fails = False
        driver.publisher.failing_recipients = {luis}

        result = await driver.publish_pending()

        assert result == (1, 1)
        assert [notice['recipient'] for notice in driver.publisher.sent] == [rosa]

    async def test_rebuilds_the_notice_of_a_block_for_failed_attempts(self) -> None:
        driver = AccountsDriver()
        await driver.register('luish')
        driver.publisher.fails = True
        for _ in range(5):
            with pytest.raises(InvalidCredentialsError):
                await driver.sign_in('luish', password=f'not-{PASSWORD}')
        driver.publisher.fails = False

        await driver.publish_pending()

        [notice] = driver.publisher.sent
        assert '5 intentos fallidos de ingreso' in notice['body']
