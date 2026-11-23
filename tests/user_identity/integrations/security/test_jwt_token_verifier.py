from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from app.user_identity.infrastructure.security.jwt_token_issuer import JwtTokenIssuer
from app.user_identity.infrastructure.security.jwt_token_verifier import (
    JwtTokenVerifier,
    public_key_of,
)
from tests.fakes.user_identity import FakeClock
from tests.user_identity.integrations.security.conftest import (
    key_pair,
    tamper_subject,
)

NOW = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)
LIFETIME = timedelta(minutes=15)


def _issued(private_key: str, user_uuid: object = None) -> str:
    issuer = JwtTokenIssuer(private_key, LIFETIME, FakeClock(NOW))
    return issuer.issue(user_uuid or uuid4())  # type: ignore[arg-type]


def _verifier(private_key: str, at: datetime = NOW) -> JwtTokenVerifier:
    return JwtTokenVerifier(public_key_of(private_key), FakeClock(at))


class TestJwtTokenVerifier:
    def test_a_token_in_force_gives_its_user(self, private_key):
        user_uuid = uuid4()
        token = _issued(private_key, user_uuid)

        assert _verifier(private_key).user_of(token) == user_uuid

    def test_an_expired_token_gives_no_user(self, private_key):
        token = _issued(private_key)

        assert _verifier(private_key, at=NOW + LIFETIME).user_of(token) is None

    def test_a_token_of_another_issuer_gives_no_user(self, private_key):
        claims = {'sub': str(uuid4()), 'iss': 'turfbook-owner', 'exp': NOW + LIFETIME}
        token = jwt.encode(claims, private_key, algorithm='RS256')

        assert _verifier(private_key).user_of(token) is None

    def test_a_tampered_token_gives_no_user(self, private_key):
        token = tamper_subject(_issued(private_key))

        assert _verifier(private_key).user_of(token) is None

    def test_a_token_signed_with_another_key_gives_no_user(self, private_key):
        other_private_key, _ = key_pair()
        token = _issued(other_private_key)

        assert _verifier(private_key).user_of(token) is None

    def test_something_that_is_not_a_token_gives_no_user(self, private_key):
        assert _verifier(private_key).user_of('not-a-token') is None
