import secrets

from app.user_identity.domain.ports.driven.security_code_generator_port import (
    SecurityCodeGeneratorPort,
)

CODE_DIGITS = 6


class SecretsSecurityCodeGenerator(SecurityCodeGeneratorPort):
    def generate(self) -> str:
        return f'{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}'
