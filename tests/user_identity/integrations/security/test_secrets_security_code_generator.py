import re

from app.user_identity.infrastructure.security.secrets_security_code_generator import (
    SecretsSecurityCodeGenerator,
)

SIX_DIGITS = re.compile(r'[0-9]{6}')


class TestSecretsSecurityCodeGenerator:
    def test_every_code_has_six_digits_even_with_leading_zeros(self):
        codes = [SecretsSecurityCodeGenerator().generate() for _ in range(500)]

        assert all(SIX_DIGITS.fullmatch(code) for code in codes)
