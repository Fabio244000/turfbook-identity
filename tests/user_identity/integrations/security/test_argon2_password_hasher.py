from app.user_identity.infrastructure.security.argon2_password_hasher import (
    Argon2PasswordHasher,
)


class TestArgon2PasswordHasher:
    def test_never_stores_the_plain_password(self):
        hashed = Argon2PasswordHasher().hash('secret1234')

        assert hashed != 'secret1234'
