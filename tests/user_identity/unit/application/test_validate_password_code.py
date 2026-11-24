from datetime import timedelta
from uuid import uuid4

import pytest

from app.user_identity.application.exceptions import (
    ProcessNotFoundError,
    SecurityCodeIncorrectError,
)
from tests.user_identity.unit.application.accounts_driver import NOW
from tests.user_identity.unit.application.passwords_driver import PasswordsDriver
from tests.user_identity.unit.application.security_codes_driver import WRONG_CODE


class TestValidatePasswordUpdate:
    async def test_the_right_code_gives_five_minutes_to_set_the_password(
        self,
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_update(rosa)
        driver.later(minutes=2)

        deadline = await driver.validate_update(rosa, process, driver.sent_code())

        assert deadline == NOW + timedelta(minutes=2 + 5)

    async def test_rejects_a_wrong_code(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_update(rosa)

        with pytest.raises(
            SecurityCodeIncorrectError, match='^The security code is incorrect.$'
        ):
            await driver.validate_update(rosa, process, WRONG_CODE)

    async def test_rejects_the_process_of_another_user(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        luis = await driver.register('luish')
        process, _ = await driver.request_update(rosa)

        with pytest.raises(ProcessNotFoundError, match='^The process does not exist.$'):
            await driver.validate_update(luis, process, driver.sent_code())

    async def test_rejects_a_process_of_recovery(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        recovery = await driver.request_recovery_of(rosa)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate_update(rosa, recovery, driver.sent_code())

    async def test_rejects_a_process_already_validated(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate_update(rosa, process, driver.sent_code())

    async def test_rejects_a_process_of_an_account_blocked_meanwhile(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_update(rosa)
        await driver.block(rosa)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate_update(rosa, process, driver.sent_code())


class TestValidatePasswordRecovery:
    async def test_the_right_code_gives_five_minutes_to_set_the_password(
        self,
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.request_recovery_of(rosa)

        deadline = await driver.validate_recovery(process, driver.sent_code())

        assert deadline == NOW + timedelta(minutes=5)

    async def test_rejects_a_process_that_does_not_exist(self) -> None:
        driver = PasswordsDriver()

        with pytest.raises(ProcessNotFoundError, match='^The process does not exist.$'):
            await driver.validate_recovery(uuid4(), WRONG_CODE)

    async def test_rejects_a_process_of_update(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        update, _ = await driver.request_update(rosa)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate_recovery(update, driver.sent_code())

    async def test_rejects_a_process_whose_day_ended(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        driver.later(hours=11, minutes=58)
        process = await driver.request_recovery_of(rosa)
        driver.later(minutes=4)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate_recovery(process, driver.sent_code())
