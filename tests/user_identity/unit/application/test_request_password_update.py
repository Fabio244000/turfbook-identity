from datetime import timedelta

import pytest

from app.user_identity.application.exceptions import (
    PasswordUpdateIntervalError,
    ProcessFailedError,
    ProcessNotAllowedError,
    SecurityCodeNotSentError,
)
from tests.user_identity.unit.application.accounts_driver import NOW
from tests.user_identity.unit.application.passwords_driver import PasswordsDriver

UPDATE_BODY = (
    'Hola Rosa, tu código para actualizar tu contraseña es {code}. Vence en 5 minutos. '
    'Si no lo pediste, ignora este mensaje.'
)


class TestRequestPasswordUpdate:
    async def test_sends_a_code_by_email_and_sms(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa', first_name='rosa')

        _, expires_at = await driver.request_update(rosa)

        [notice] = driver.publisher.sent
        assert notice['recipient'] == rosa
        assert notice['notifiers'] == ['email', 'sms']
        assert notice['code'] == driver.sent_code()
        assert notice['subject'] == 'Tu código de seguridad de TurfBook'
        assert notice['body'] == UPDATE_BODY
        assert expires_at == NOW + timedelta(minutes=5)

    async def test_a_new_code_goes_on_in_the_process(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        first, _ = await driver.request_update(rosa)
        driver.later(minutes=10)

        second, _ = await driver.request_update(rosa)

        assert second == first

    async def test_takes_at_least_the_floor_of_a_code_request(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')

        await driver.request_update(rosa)

        assert driver.duration.floors == [1.0]

    async def test_updates_again_once_the_interval_passed(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        previous = await driver.updated(rosa)
        driver.later(days=30)

        process, _ = await driver.request_update(rosa)

        assert process != previous

    async def test_a_recovery_does_not_count_for_the_interval(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        recovery = await driver.recovered(rosa)
        driver.later(days=1)

        process, _ = await driver.request_update(rosa)

        assert process != recovery


class TestRequestPasswordUpdateRejections:
    async def test_rejects_the_data_of_another_account(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        luis = await driver.register('luish')

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_update(
                rosa, driver.cellphones[luis], driver.emails[luis]
            )

    async def test_rejects_an_email_of_another_account(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_update(rosa, email='otro@gmail.com')

    async def test_rejects_a_blocked_account(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.block(rosa)

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_update(rosa)

    async def test_a_rejection_takes_the_floor_too(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')

        with pytest.raises(ProcessNotAllowedError):
            await driver.request_update(rosa, email='otro@gmail.com')

        assert driver.duration.floors == [1.0]

    async def test_rejects_an_update_within_the_interval(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.updated(rosa)
        driver.later(days=14)

        with pytest.raises(
            PasswordUpdateIntervalError,
            match='^You can only update your password once every 30 days.$',
        ):
            await driver.request_update(rosa)

    async def test_rejects_an_update_a_moment_before_the_interval(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.updated(rosa)
        driver.later(days=30, seconds=-1)

        with pytest.raises(PasswordUpdateIntervalError):
            await driver.request_update(rosa)

    async def test_an_update_of_today_answers_the_interval_not_tomorrow(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.updated(rosa)
        driver.later(hours=1)

        with pytest.raises(PasswordUpdateIntervalError):
            await driver.request_update(rosa)

    async def test_rejects_a_new_process_the_day_one_failed(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.failed_update(rosa)
        driver.later(hours=1)

        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.request_update(rosa)

    async def test_a_code_that_could_not_be_sent_answers_its_own_error(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        driver.publisher.fails = True

        with pytest.raises(
            SecurityCodeNotSentError,
            match='^The security code could not be sent. Try again.$',
        ):
            await driver.request_update(rosa)
