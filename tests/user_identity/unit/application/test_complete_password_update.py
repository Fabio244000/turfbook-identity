from contextlib import suppress

import pytest

from app.user_identity.application.exceptions import (
    InvalidNewPasswordError,
    PasswordAttemptsExceededError,
    PasswordDeadlineExpiredError,
    PasswordRejectedError,
    ProcessFailedError,
    ProcessNotFoundError,
    SecurityCodeNotValidatedError,
)
from app.user_identity.domain.exceptions import InvalidCredentialsError
from tests.user_identity.unit.application.accounts_driver import PASSWORD
from tests.user_identity.unit.application.passwords_driver import (
    NEW_PASSWORD,
    SIMILAR_PASSWORD,
    PasswordsDriver,
)


class TestCompletePasswordUpdate:
    async def test_the_new_password_signs_in_and_the_old_one_no_longer(
        self,
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        await driver.complete_update(rosa, process)

        await driver.sign_in('qarosa', NEW_PASSWORD)
        with pytest.raises(InvalidCredentialsError):
            await driver.sign_in('qarosa', PASSWORD)

    async def test_the_session_goes_on(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        session = await driver.sign_in('qarosa')
        process = await driver.validated_update(rosa)

        await driver.complete_update(rosa, process)

        assert await driver.refresh(session)

    async def test_accepts_a_password_that_differs_in_three_characters(
        self,
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        await driver.complete_update(rosa, process, 'GrassElSol2O29?')

        await driver.sign_in('qarosa', 'GrassElSol2O29?')

    async def test_a_rejected_password_is_corrected_within_the_deadline(
        self,
    ) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)
        with pytest.raises(PasswordRejectedError):
            await driver.complete_update(rosa, process, SIMILAR_PASSWORD)
        driver.later(minutes=3)

        await driver.complete_update(rosa, process)

        await driver.sign_in('qarosa', NEW_PASSWORD)

    async def test_rejects_a_second_completion(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)
        await driver.complete_update(rosa, process)

        with pytest.raises(ProcessNotFoundError, match='^The process does not exist.$'):
            await driver.complete_update(rosa, process, 'OtraCancha#Lima8')


class TestCompletePasswordUpdateRejections:
    @pytest.mark.parametrize(
        'new_password', ['grasselsol2026!', SIMILAR_PASSWORD, 'GrassElSol2029?']
    )
    async def test_rejects_a_password_too_similar(self, new_password: str) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        with pytest.raises(
            PasswordRejectedError,
            match='^The new password is too similar to the current one.$',
        ):
            await driver.complete_update(rosa, process, new_password)

    async def test_rejects_a_wrong_current_password(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        with pytest.raises(
            PasswordRejectedError, match='^The current password is incorrect.$'
        ):
            await driver.complete_update(
                rosa, process, current_password='GrassElLuna2026!'
            )

    async def test_rejects_two_different_entries(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        with pytest.raises(
            PasswordRejectedError, match='^The passwords do not match.$'
        ):
            await driver.complete_update(
                rosa, process, confirmation='CanchaVerde#Lima8'
            )

    async def test_rejects_a_short_password_by_field(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)

        with pytest.raises(InvalidNewPasswordError) as raised:
            await driver.complete_update(rosa, process, 'corta')

        assert raised.value.causes == (
            ('new_password', 'Password must be between 15 and 64 characters.'),
        )

    async def test_rejects_a_code_not_validated(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process, _ = await driver.request_update(rosa)

        with pytest.raises(
            SecurityCodeNotValidatedError,
            match='^The security code has not been validated.$',
        ):
            await driver.complete_update(rosa, process)

    async def test_rejects_the_process_of_another_user(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        luis = await driver.register('luish')
        process = await driver.validated_update(rosa)

        with pytest.raises(ProcessNotFoundError):
            await driver.complete_update(luis, process)


class TestCompletePasswordUpdateLimits:
    async def test_after_the_deadline_the_process_fails(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)
        driver.later(minutes=6)

        with pytest.raises(
            PasswordDeadlineExpiredError,
            match='^The time to set the new password has expired.$',
        ):
            await driver.complete_update(rosa, process)
        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.complete_update(rosa, process)

    async def test_the_fifth_rejection_fails_the_process(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)
        for _ in range(4):
            with suppress(PasswordRejectedError):
                await driver.complete_update(rosa, process, SIMILAR_PASSWORD)

        with pytest.raises(
            PasswordAttemptsExceededError,
            match=(
                '^You have exceeded the attempts to set the password. '
                'Try again tomorrow.$'
            ),
        ):
            await driver.complete_update(rosa, process, SIMILAR_PASSWORD)
        with pytest.raises(ProcessFailedError, match='^Try again tomorrow.$'):
            await driver.complete_update(rosa, process)

    async def test_a_format_error_does_not_count_as_a_rejection(self) -> None:
        driver = PasswordsDriver()
        rosa = await driver.register('qarosa')
        process = await driver.validated_update(rosa)
        for _ in range(4):
            with suppress(PasswordRejectedError):
                await driver.complete_update(rosa, process, SIMILAR_PASSWORD)
        with suppress(InvalidNewPasswordError):
            await driver.complete_update(rosa, process, 'corta')

        await driver.complete_update(rosa, process)

        await driver.sign_in('qarosa', NEW_PASSWORD)
