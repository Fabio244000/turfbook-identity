from app.user_identity.infrastructure.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)


class TestArgon2PasswordHasher:
    def test_never_stores_the_plain_password(self):
        hashed = Argon2PasswordHasher().hash('secret1234')

        assert hashed != 'secret1234'

    def test_without_a_hash_no_password_matches(self):
        matches = Argon2PasswordHasher().verify('GrassElSol2026!', None)

        assert matches is False
