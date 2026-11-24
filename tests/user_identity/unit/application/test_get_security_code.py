from datetime import timedelta

import pytest

from app.user_identity.application.exceptions import (
    EmailAlreadyVerifiedError,
    NoProcessInProgressError,
    SecurityCodeDeliveredError,
    SecurityCodeLimitError,
    SupportCodeLimitError,
    UserNotFoundError,
)
from tests.user_identity.unit.application.accounts_driver import NOW
from tests.user_identity.unit.application.security_codes_driver import (
    SecurityCodesDriver,
)


class TestGetSecurityCode:
    async def test_shows_the_code_in_force(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, expires_at = await driver.request_verification(rosa)

        support = await driver.support_code(driver.cellphones[rosa])

        assert support.process_uuid == process
        assert support.code == driver.sent_code()
        assert support.code_expires_at == expires_at
        assert not support.generated

    async def test_generates_a_code_when_the_last_one_expired(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=40)

        support = await driver.support_code(driver.cellphones[rosa])

        assert support.generated
        assert support.code != driver.sent_code()
        assert support.code_expires_at == NOW + timedelta(minutes=45)

    async def test_the_generated_code_is_not_sent_to_the_user(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.later(minutes=40)

        await driver.support_code(driver.cellphones[rosa])

        assert len(driver.publisher.attempted) == 1

    async def test_the_generated_code_does_not_count_among_the_user_codes(
        self,
    ) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.later(minutes=40)
        await driver.support_code(driver.cellphones[rosa])

        await driver.request_verification(rosa)
        await driver.request_verification(rosa)

        with pytest.raises(SecurityCodeLimitError):
            await driver.request_verification(rosa)

    async def test_the_generated_code_verifies_the_email(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        driver.later(minutes=40)
        support = await driver.support_code(driver.cellphones[rosa])

        await driver.validate(rosa, process, support.code)

        with pytest.raises(EmailAlreadyVerifiedError):
            await driver.request_verification(rosa)

    async def test_generates_a_second_code_when_the_first_one_expired(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.later(minutes=40)
        first = await driver.support_code(driver.cellphones[rosa])
        driver.later(minutes=5)

        second = await driver.support_code(driver.cellphones[rosa])

        assert second.generated
        assert second.code != first.code

    async def test_generates_a_code_just_before_the_grace_period_ends(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.later(minutes=5 + 59)

        support = await driver.support_code(driver.cellphones[rosa])

        assert support.generated


class TestGetSecurityCodeRejections:
    async def test_rejects_a_third_code_of_support(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        for _ in range(2):
            driver.later(minutes=10)
            await driver.support_code(driver.cellphones[rosa])
        driver.later(minutes=10)

        with pytest.raises(
            SupportCodeLimitError,
            match='^Support cannot generate more security codes.$',
        ):
            await driver.support_code(driver.cellphones[rosa])

    async def test_rejects_replacing_a_code_whose_attempts_were_spent(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        await driver.fail_validations(rosa, process)

        with pytest.raises(
            SecurityCodeDeliveredError,
            match='^The security code was delivered: it cannot be replaced.$',
        ):
            await driver.support_code(driver.cellphones[rosa])

    async def test_rejects_a_cellphone_without_account(self) -> None:
        driver = SecurityCodesDriver()

        with pytest.raises(UserNotFoundError, match='^The user does not exist.$'):
            await driver.support_code('+51900000777')

    async def test_rejects_a_user_without_a_process_in_progress(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')

        with pytest.raises(
            NoProcessInProgressError, match='^There is no process in progress.$'
        ):
            await driver.support_code(driver.cellphones[rosa])

    async def test_rejects_a_process_of_another_type(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)

        with pytest.raises(NoProcessInProgressError):
            await driver.support_code(driver.cellphones[rosa], 'password_update')

    async def test_rejects_a_process_whose_day_ended(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.later(hours=12)

        with pytest.raises(NoProcessInProgressError):
            await driver.support_code(driver.cellphones[rosa])
