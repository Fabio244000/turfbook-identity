from datetime import timedelta

import pytest

from app.user_identity.application.exceptions import (
    EmailAlreadyVerifiedError,
    NoProcessInProgressError,
    ProcessFailedError,
    ProcessNotAllowedError,
    SecurityCodeLimitError,
    SecurityCodeNotSentError,
)
from tests.user_identity.unit.application.accounts_driver import NOW
from tests.user_identity.unit.application.security_codes_driver import (
    SecurityCodesDriver,
)

VERIFICATION_BODY = (
    'Hola Rosa, tu código para verificar tu correo es {code}. Vence en 5 minutos. '
    'Si no lo pediste, ignora este mensaje.'
)


class TestRequestEmailVerification:
    async def test_sends_a_code_only_to_the_account_email(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa', first_name='rosa')

        _, expires_at = await driver.request_verification(rosa)

        [notice] = driver.publisher.sent
        assert notice['recipient'] == rosa
        assert notice['notifiers'] == ['email']
        assert notice['code'] == driver.sent_code()
        assert notice['subject'] == 'Tu código de seguridad de TurfBook'
        assert notice['body'] == VERIFICATION_BODY
        assert expires_at == NOW + timedelta(minutes=5)

    async def test_a_new_code_within_the_window_goes_on_in_the_process(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        first, _ = await driver.request_verification(rosa)
        driver.later(minutes=30)

        second, _ = await driver.request_verification(rosa)

        assert second == first

    async def test_a_process_left_open_at_midnight_does_not_stop_the_next_day(
        self,
    ) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        yesterday, _ = await driver.request_verification(rosa)
        driver.later(days=1)

        today, _ = await driver.request_verification(rosa)

        assert today != yesterday

    async def test_starts_again_the_day_after_a_process_failed(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        failed = await driver.failed_process(rosa)
        driver.later(hours=12, minutes=1)

        process, _ = await driver.request_verification(rosa)

        assert process != failed


class TestRequestEmailVerificationRejections:
    async def test_rejects_an_account_without_email(self) -> None:
        driver = SecurityCodesDriver()
        nameless = driver.user_without_email()

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_verification(nameless)

    async def test_rejects_a_blocked_account(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.block(rosa)

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_verification(rosa)

    async def test_rejects_a_closed_account(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.block(rosa)
        driver.later(days=7)
        await driver.close_expired()

        with pytest.raises(
            ProcessNotAllowedError, match='^It is not possible to start the process.$'
        ):
            await driver.request_verification(rosa)

    async def test_rejects_an_email_already_verified_without_a_notice(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        await driver.validate(rosa, process, driver.sent_code())

        with pytest.raises(
            EmailAlreadyVerifiedError, match='^The email is already verified.$'
        ):
            await driver.request_verification(rosa)
        assert len(driver.publisher.attempted) == 1

    async def test_rejects_a_fourth_code_in_the_process(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        for _ in range(3):
            await driver.request_verification(rosa)

        with pytest.raises(
            SecurityCodeLimitError,
            match='^You cannot request more security codes, try again later.$',
        ):
            await driver.request_verification(rosa)

    async def test_rejects_a_new_process_the_day_one_failed(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.failed_process(rosa)
        driver.later(hours=11)

        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.request_verification(rosa)


class TestRequestEmailVerificationNotSent:
    async def test_a_code_that_could_not_be_sent_answers_its_own_error(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        driver.publisher.fails = True

        with pytest.raises(
            SecurityCodeNotSentError,
            match='^The security code could not be sent. Try again.$',
        ):
            await driver.request_verification(rosa)

    async def test_a_code_that_could_not_be_sent_is_not_counted(self) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        await driver.request_verification(rosa)
        driver.publisher.fails = True
        with pytest.raises(SecurityCodeNotSentError):
            await driver.request_verification(rosa)
        driver.publisher.fails = False

        await driver.request_verification(rosa)
        await driver.request_verification(rosa)

        with pytest.raises(SecurityCodeLimitError):
            await driver.request_verification(rosa)

    async def test_the_previous_code_still_validates_when_the_new_one_was_not_sent(
        self,
    ) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_verification(rosa)
        previous = driver.sent_code()
        driver.publisher.fails = True
        with pytest.raises(SecurityCodeNotSentError):
            await driver.request_verification(rosa)

        await driver.validate(rosa, process, previous)

        with pytest.raises(EmailAlreadyVerifiedError):
            await driver.request_verification(rosa)

    async def test_a_first_code_that_could_not_be_sent_leaves_no_process(
        self,
    ) -> None:
        driver = SecurityCodesDriver()
        rosa = await driver.register('qarosa')
        driver.publisher.fails = True

        with pytest.raises(SecurityCodeNotSentError):
            await driver.request_verification(rosa)

        with pytest.raises(NoProcessInProgressError):
            await driver.support_code(driver.cellphones[rosa])
