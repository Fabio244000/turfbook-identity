from datetime import UTC, datetime
from typing import Any

from app.user_identity.domain.entities.user import User

REGISTERED_AT = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
ARGON2_HASH = '$argon2id$v=19$m=65536,t=3,p=4$c2FsdHNhbHRzYWx0$aGFzaGhhc2hoYXNoaGFzaA'


class TestUserRebuiltFromStoredData:
    def test_is_not_validated_again_as_an_input(self) -> None:
        stored: dict[str, Any] = {
            'first_name': 'rosa',
            'last_name': 'quispe',
            'cellphone': '+51987654321',
            'username': 'rosa01',
            'password': ARGON2_HASH,
            'email': None,
            'created_at': REGISTERED_AT,
            'updated_at': REGISTERED_AT,
        }

        user = User(**stored)

        assert (user.password, user.email) == (ARGON2_HASH, None)
