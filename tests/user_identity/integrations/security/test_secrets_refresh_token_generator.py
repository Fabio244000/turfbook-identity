import re

from app.user_identity.infrastructure.security.secrets_refresh_token_generator import (
    SecretsRefreshTokenGenerator,
)

BASE64URL_256_BITS = re.compile(r'[A-Za-z0-9_-]{43}')
SHA256_OF_ABC = 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad'


def _generator() -> SecretsRefreshTokenGenerator:
    return SecretsRefreshTokenGenerator(token_bytes=32)


class TestSecretsRefreshTokenGenerator:
    def test_generates_the_configured_random_bytes_in_base64url(self):
        token = _generator().generate()

        assert BASE64URL_256_BITS.fullmatch(token)

    def test_hashes_with_sha256_in_hex(self):
        token_hash = _generator().hash('abc')

        assert token_hash == SHA256_OF_ABC
