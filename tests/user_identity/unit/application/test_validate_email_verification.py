from uuid import uuid4

import pytest

from app.user_identity.application.exceptions import (
    EmailAlreadyVerifiedError,
    ProcessFailedError,
    ProcessNotFoundError,
    SecurityCodeExhaustedError,
    SecurityCodeExpiredError,
    SecurityCodeIncorrectError,
)
from tests.user_identity.unit.application.security_codes_driver import (
    WRONG_CODE,
    SecurityCodesDriver,
)


class TestValidateEmailVerification:
    async def test_the_right_code_verifies_the_email(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)

        await driver.validate(rosa, process, driver.sent_code())

        with pytest.raises(EmailAlreadyVerifiedError):
            await driver.request_verification(rosa)

    async def test_a_code_still_valid_at_minute_four(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=4)

        await driver.validate(rosa, process, driver.sent_code())

        with pytest.raises(EmailAlreadyVerifiedError):
            await driver.request_verification(rosa)

    async def test_only_the_last_code_requested_validates(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        replaced = driver.sent_code()
        await driver.request_verification(rosa)
        last = driver.sent_code()

        with pytest.raises(
            SecurityCodeIncorrectError, match='^The security code is incorrect.$'
        ):
            await driver.validate(rosa, process, replaced)
        await driver.validate(rosa, process, last)

    async def test_after_spending_the_attempts_another_code_can_be_requested(
        self,
    ) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        await driver.fail_validations(rosa, process)

        await driver.request_verification(rosa)

        await driver.validate(rosa, process, driver.sent_code())


class TestValidateEmailVerificationRejections:
    async def test_rejects_an_expired_code(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=6)

        with pytest.raises(
            SecurityCodeExpiredError, match='^The security code has expired.$'
        ):
            await driver.validate(rosa, process, driver.sent_code())

    async def test_an_expired_code_does_not_count_an_attempt(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=6)
        for _ in range(3):
            with pytest.raises(SecurityCodeExpiredError):
                await driver.validate(rosa, process, WRONG_CODE)

        support = await driver.support_code(driver.cellphones[rosa])

        assert support.generated

    async def test_rejects_a_fourth_attempt_even_with_the_right_code(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        await driver.fail_validations(rosa, process)

        with pytest.raises(
            SecurityCodeExhaustedError, match='^You can no longer validate the code.$'
        ):
            await driver.validate(rosa, process, driver.sent_code())

    async def test_the_last_attempt_of_the_last_code_fails_the_process(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process = await driver.failed_process(rosa)

        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.validate(rosa, process, driver.sent_code())

    async def test_rejects_the_process_of_another_user(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        luis = await driver.register('luish')
        process, _ = await driver.request_verification(rosa)

        with pytest.raises(ProcessNotFoundError, match='^The process does not exist.$'):
            await driver.validate(luis, process, driver.sent_code())

    async def test_rejects_a_process_that_does_not_exist(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')

        with pytest.raises(ProcessNotFoundError, match='^The process does not exist.$'):
            await driver.validate(rosa, uuid4(), WRONG_CODE)

    async def test_rejects_a_code_already_used(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        await driver.validate(rosa, process, driver.sent_code())

        with pytest.raises(ProcessNotFoundError):
            await driver.validate(rosa, process, driver.sent_code())

    async def test_rejects_a_code_of_a_process_whose_day_ended(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        driver.later(hours=11, minutes=58)
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=4)

        with pytest.raises(ProcessNotFoundError):
            await driver.validate(rosa, process, driver.sent_code())
