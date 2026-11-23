from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
import pytest

from app.user_identity.infrastructure.security.jwt_token_issuer import JwtTokenIssuer
from tests.fakes.user_identity import FakeClock
from tests.user_identity.integrations.security.conftest import (
    key_pair,
    tamper_subject,
)

NOW = datetime(2026, 10, 29, 12, 0, tzinfo=UTC)
LIFETIME = timedelta(minutes=15)


@pytest.fixture
def issuer(private_key: str) -> JwtTokenIssuer:
    return JwtTokenIssuer(
        private_key=private_key,
        lifetime=LIFETIME,
        clock=FakeClock(NOW),
    )


def _decode(token: str, public_key: str) -> dict[str, Any]:
    # NOW is a fixed moment, so `exp` is checked by value, not against the real clock.
    return jwt.decode(
        token, public_key, algorithms=['RS256'], options={'verify_exp': False}
    )


class TestJwtTokenIssuer:
    def test_signs_with_rs256_and_the_public_key_verifies_it(self, issuer, public_key):
        token = issuer.issue(uuid4())

        assert jwt.get_unverified_header(token)['alg'] == 'RS256'
        assert _decode(token, public_key)

    def test_identifies_the_user_and_the_issuer(self, issuer, public_key):
        user_uuid = uuid4()

        claims = _decode(issuer.issue(user_uuid), public_key)

        assert claims['sub'] == str(user_uuid)
        assert claims['iss'] == 'turfbook-identity'

    def test_lasts_its_lifetime_from_the_clock_time(self, issuer, public_key):
        claims = _decode(issuer.issue(uuid4()), public_key)

        assert claims['iat'] == int(NOW.timestamp())
        assert claims['exp'] == int((NOW + LIFETIME).timestamp())

    def test_another_public_key_cannot_verify_it(self, issuer):
        _, other_public_key = key_pair()

        with pytest.raises(jwt.InvalidSignatureError):
            _decode(issuer.issue(uuid4()), other_public_key)

    def test_a_tampered_payload_fails_verification(self, issuer, public_key):
        token = tamper_subject(issuer.issue(uuid4()))

        with pytest.raises(jwt.InvalidSignatureError):
            _decode(token, public_key)
