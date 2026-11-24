from datetime import timedelta
from uuid import UUID

import pytest

from app.user_identity.application.exceptions import (
    ProcessFailedError,
    ProcessNotAllowedError,
    RecoveryLimitError,
)
from tests.user_identity.unit.application.accounts_driver import NOW
from tests.user_identity.unit.application.passwords_driver import PasswordsDriver

RECOVERY_BODY = (
    'Hola Rosa, tu código para recuperar tu contraseña es {code}. Vence en 5 minutos. '
    'Si no lo pediste, ignora este mensaje.'
)
# NOW is Thursday 2026-11-05, 12:00 in Lima.
MONDAY = NOW - timedelta(days=3)


class TestRequestPasswordRecovery:
    async def test_sends_a_code_by_email_and_sms(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa', first_name='rosa')

        _, expires_at = await driver.request_recovery(
            driver.cellphones[rosa], driver.emails[rosa]
        )

        [notice] = driver.publisher.sent
        assert notice['recipient'] == rosa
        assert notice['notifiers'] == ['email', 'sms']
        assert notice['code'] == driver.sent_code()
        assert notice['body'] == RECOVERY_BODY
        assert expires_at == NOW + timedelta(minutes=5)

    async def test_an_unknown_account_takes_the_floor_too(self) -> None:
        driver = PasswordsDriver()

        with pytest.raises(ProcessNotAllowedError):
            await driver.request_recovery('+51900000999', 'nadie@gmail.com')

        assert driver.duration.floors == [1.0]

    async def test_an_abandoned_process_does_not_stop_a_new_one(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        abandoned = await driver.request_recovery_of(rosa)
        driver.later(hours=2, minutes=6)

        process = await driver.request_recovery_of(rosa)

        assert process != abandoned

    async def test_starts_again_the_day_after_a_process_failed(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        driver.later(hours=10)
        failed = await driver.failed_recovery(rosa)
        driver.later(hours=1)
        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.request_recovery_of(rosa)
        driver.later(hours=1, minutes=1)

        process = await driver.request_recovery_of(rosa)

        assert process != failed


class TestRequestPasswordRecoveryRejections:
    async def test_rejects_a_cellphone_with_another_email(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_recovery(driver.cellphones[rosa], 'otro@gmail.com')

    async def test_rejects_an_unknown_account(self) -> None:
        driver = PasswordsDriver()

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_recovery('+51900000999', 'nadie@gmail.com')

    async def test_rejects_an_account_without_password(self) -> None:
        driver = PasswordsDriver()
        driver.uow.with_user(cellphone='+51900000999', email='rosa.fb@gmail.com')

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_recovery('+51900000999', 'rosa.fb@gmail.com')

    async def test_rejects_a_blocked_account(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.block(rosa)

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_recovery_of(rosa)


async def _four_failed_recoveries(driver: PasswordsDriver) -> tuple[UUID, list[UUID]]:
    """Rosa fails a recovery from Monday to Thursday (NOW), one per day."""
    rosa = await driver.register('qarosa')
    driver.clock.current = MONDAY
    failed = []
    for _ in range(4):
        failed.append(await driver.failed_recovery(rosa))
        driver.later(days=1)
    return rosa, failed


class TestRequestPasswordRecoveryWeek:
    async def test_rejects_a_recovery_after_four_failed_in_the_week(self) -> None:
        driver = PasswordsDriver()
        rosa, _ = await _four_failed_recoveries(driver)
        driver.clock.current = NOW + timedelta(days=2)

        with pytest.raises(
            RecoveryLimitError,
            match=(
                r'^You cannot recover your password. Contact TurfBook at '
                r'\+51 999999998 or turfbook@gmail.com.$'
            ),
        ):
            await driver.request_recovery_of(rosa)

    async def test_the_limit_starts_again_on_monday(self) -> None:
        driver = PasswordsDriver()
        rosa, failed = await _four_failed_recoveries(driver)
        # Monday 2026-11-09, 00:01 in Lima.
        driver.clock.current = MONDAY + timedelta(days=7, hours=-12, minutes=1)

        process = await driver.request_recovery_of(rosa)

        assert process not in failed

    async def test_the_limit_is_checked_before_the_failure_of_today(self) -> None:
        driver = PasswordsDriver()
        rosa, _ = await _four_failed_recoveries(driver)
        driver.clock.current = NOW + timedelta(hours=1)

        with pytest.raises(RecoveryLimitError):
            await driver.request_recovery_of(rosa)
