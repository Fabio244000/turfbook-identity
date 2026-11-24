from contextlib import suppress

import pytest

from app.user_identity.application.exceptions import (
    PasswordAttemptsExceededError,
    PasswordRejectedError,
    ProcessFailedError,
)
from app.user_identity.domain.exceptions import InvalidRefreshTokenError
from tests.user_identity.unit.application.accounts_driver import PASSWORD
from tests.user_identity.unit.application.passwords_driver import (
    NEW_PASSWORD,
    SIMILAR_PASSWORD,
    PasswordsDriver,
)


class TestCompletePasswordRecovery:
    async def test_the_new_password_signs_in(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_recovery(rosa)

        await driver.complete_recovery(process)

        await driver.sign_in('qarosa', NEW_PASSWORD)

    async def test_closes_the_session(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        session = await driver.sign_in('qarosa')
        process = await driver.validated_recovery(rosa)

        await driver.complete_recovery(process)

        with pytest.raises(InvalidRefreshTokenError):
            await driver.refresh(session)

    async def test_accepts_a_password_close_to_the_current_one(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_recovery(rosa)

        await driver.complete_recovery(process, SIMILAR_PASSWORD)

        await driver.sign_in('qarosa', SIMILAR_PASSWORD)


class TestCompletePasswordRecoveryRejections:
    async def test_rejects_the_current_password(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_recovery(rosa)

        with pytest.raises(
            PasswordRejectedError,
            match='^The new password must be different from the current one.$',
        ):
            await driver.complete_recovery(process, PASSWORD)

    async def test_rejects_two_different_entries(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_recovery(rosa)

        with pytest.raises(
            PasswordRejectedError, match='^The passwords do not match.$'
        ):
            await driver.complete_recovery(process, confirmation='CanchaVerde#Lima8')

    async def test_the_fifth_rejection_fails_the_process(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_recovery(rosa)
        await driver.reject_recoveries(process, times=4)

        with pytest.raises(PasswordAttemptsExceededError):
            await driver.complete_recovery(process, PASSWORD)
        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.complete_recovery(process)

    async def test_a_process_failed_by_rejections_counts_for_the_day(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_recovery(rosa)
        await driver.reject_recoveries(process, times=4)
        with suppress(PasswordAttemptsExceededError):
            await driver.complete_recovery(process, PASSWORD)

        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.request_recovery_of(rosa)
