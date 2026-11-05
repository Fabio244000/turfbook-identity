from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.user_identity.domain.ports.output.password_hasher_port import (
    PasswordHasherPort,
)

# Its value does not matter: without a stored hash the answer is always False.
_DUMMY_PASSWORD = 'turfbook-dummy-password'


class Argon2PasswordHasher(PasswordHasherPort):
    password_hasher = PasswordHash((Argon2Hasher(),))
    # Hashed once per environment, with the same parameters as the real hashes, so
    # verifying against it takes as long as a real verification.
    _dummy_hash = password_hasher.hash(_DUMMY_PASSWORD)

    def hash(self, password: str) -> str:
        return str(self.password_hasher.hash(password))

    def verify(self, password: str, hashed: str | None) -> bool:
        if hashed is None:
            self.password_hasher.verify(password, self._dummy_hash)
            return False
        return bool(self.password_hasher.verify(password, hashed))
