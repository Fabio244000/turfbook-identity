"""The life of a security process, the same for the three of them: the user's window,
support's grace, the deadline of a validated process and midnight."""

from uuid import UUID

import pytest

from app.user_identity.application.exceptions import (
    NoProcessInProgressError,
    ProcessFailedError,
    ProcessNotFoundError,
    SecurityCodeAlreadyValidatedError,
    SecurityCodeLimitError,
    SupportProcessValidatedError,
)
from tests.user_identity.unit.application.passwords_driver import PasswordsDriver


async def _request(driver: PasswordsDriver, user: UUID, process_type: str) -> UUID:
    if process_type == 'email_verification':
        process, _ = await driver.request_verification(user)
        return process
    return await driver.request_recovery_of(user)


PROCESS_TYPES = ['email_verification', 'password_recovery']


@pytest.mark.parametrize('process_type', PROCESS_TYPES)
class TestUserWindow:
    async def test_a_code_within_the_window_goes_on_in_the_process(
        self, process_type: str
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        first = await _request(driver, rosa, process_type)
        driver.later(minutes=40)

        second = await _request(driver, rosa, process_type)

        assert second == first

    async def test_rejects_a_code_after_the_window_while_support_may_help(
        self, process_type: str
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await _request(driver, rosa, process_type)
        driver.later(minutes=40)
        await _request(driver, rosa, process_type)
        driver.later(minutes=50)

        with pytest.raises(
            SecurityCodeLimitError,
            match='^You cannot request more security codes, try again later.$',
        ):
            await _request(driver, rosa, process_type)

    async def test_support_generates_a_code_after_the_window(
        self, process_type: str
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await _request(driver, rosa, process_type)
        driver.later(minutes=40)
        await _request(driver, rosa, process_type)
        driver.later(minutes=50)

        support = await driver.support_code(driver.cellphones[rosa], process_type)

        assert support.process_uuid == process
        assert support.generated

    async def test_an_abandoned_process_closes_and_a_new_one_starts(
        self, process_type: str
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        abandoned = await _request(driver, rosa, process_type)
        driver.later(minutes=40)
        await _request(driver, rosa, process_type)
        # Its last code expired at minute 45; support's grace ended at minute 105.
        driver.later(minutes=66)

        process = await _request(driver, rosa, process_type)

        assert process != abandoned

    async def test_support_finds_no_process_once_it_was_abandoned(
        self, process_type: str
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await _request(driver, rosa, process_type)
        driver.later(minutes=5 + 60)

        with pytest.raises(NoProcessInProgressError):
            await driver.support_code(driver.cellphones[rosa], process_type)

    async def test_midnight_closes_a_process_before_its_window(
        self, process_type: str
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        driver.later(hours=11, minutes=30)
        before_midnight = await _request(driver, rosa, process_type)
        driver.later(minutes=31)

        process = await _request(driver, rosa, process_type)

        assert process != before_midnight


class TestUserWindowValidation:
    async def test_a_code_requested_at_minute_59_validates_at_minute_62(
        self,
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.later(minutes=59)
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=3)

        await driver.validate(rosa, process, driver.sent_code())

    async def test_rejects_a_code_of_a_process_already_abandoned(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.request_recovery_of(rosa)
        code = driver.sent_code()
        driver.later(minutes=5 + 60)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate_recovery(process, code)


class TestValidatedProcess:
    async def test_rejects_a_new_code_once_validated(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.validated_recovery(rosa)

        with pytest.raises(
            SecurityCodeAlreadyValidatedError,
            match='^The security code was already validated. Set your new password.$',
        ):
            await driver.request_recovery_of(rosa)

    async def test_support_cannot_give_a_code_once_validated(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.validated_update(rosa)

        with pytest.raises(
            SupportProcessValidatedError,
            match=(
                '^The security code was already validated: '
                'the user must set the new password.$'
            ),
        ):
            await driver.support_code(driver.cellphones[rosa], 'password_update')

    async def test_a_validated_process_left_after_its_deadline_failed(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.validated_recovery(rosa)
        driver.later(minutes=6)

        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.request_recovery_of(rosa)

    async def test_keeps_its_deadline_after_the_window(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.request_recovery_of(rosa)
        driver.later(minutes=58)
        process = await driver.request_recovery_of(rosa)
        await driver.validate_recovery(process, driver.sent_code())
        driver.later(minutes=4)

        await driver.complete_recovery(process)

    async def test_support_finds_no_process_after_its_deadline(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        await driver.validated_recovery(rosa)
        driver.later(minutes=6)

        with pytest.raises(NoProcessInProgressError):
            await driver.support_code(driver.cellphones[rosa], 'password_recovery')
