from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.domain.ports.output.password_hasher_port import PasswordHasherPort


class Argon2PasswordHasher(PasswordHasherPort):
    password_hasher = PasswordHash((Argon2Hasher(),))

    def hash(self, password: str) -> str:
        return str(self.password_hasher.hash(password))

    def verify(self, password: str, hashed: str) -> bool:
        return bool(self.password_hasher.verify(password, hashed))
