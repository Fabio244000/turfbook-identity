from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from alembic import command
from app.migrations.handler import ALEMBIC_INIT_PATH
from config.settings import settings

# The revisions right before each migration of `users`.
BEFORE_E164_CELLPHONES = '526c4e04b55e'
BEFORE_ACCOUNT_STATE = 'bf64ac9ccdb6'
REGISTERED_AT = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _insert_user(engine: Engine, user_uuid: UUID, cellphone: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone,'
                ' created_at, updated_at)'
                " VALUES (:uuid, 'rosa', 'quispe', :cellphone, :at, :at)"
            ),
            {'uuid': user_uuid, 'cellphone': cellphone, 'at': REGISTERED_AT},
        )


def _stored_cellphone(engine: Engine, user_uuid: UUID) -> str:
    with engine.connect() as connection:
        return str(
            connection.execute(
                text('SELECT cellphone FROM users WHERE uuid = :uuid'),
                {'uuid': user_uuid},
            ).scalar_one()
        )


def _delete_user(engine: Engine, user_uuid: UUID) -> None:
    with engine.begin() as connection:
        connection.execute(
            text('DELETE FROM users WHERE uuid = :uuid'), {'uuid': user_uuid}
        )


def _stored_cellphone_after_upgrade(old_cellphone: str) -> str:
    """Inserts a user with the old format at the previous revision, upgrades to head
    and returns what is stored; the database always ends at head, without the user."""
    config = Config(str(ALEMBIC_INIT_PATH))
    engine = create_engine(settings.database_url)
    user_uuid = uuid4()
    command.downgrade(config, BEFORE_E164_CELLPHONES)
    try:
        _insert_user(engine, user_uuid, old_cellphone)
        command.upgrade(config, 'head')
        return _stored_cellphone(engine, user_uuid)
    finally:
        command.upgrade(config, 'head')
        _delete_user(engine, user_uuid)
        engine.dispose()


def _account_state_after_upgrade() -> tuple[Any, ...]:
    """Inserts a user at the revision before the account state, upgrades to head and
    returns its state; the database always ends at head, without the user."""
    config = Config(str(ALEMBIC_INIT_PATH))
    engine = create_engine(settings.database_url)
    user_uuid = uuid4()
    command.downgrade(config, BEFORE_ACCOUNT_STATE)
    try:
        _insert_user(engine, user_uuid, f'+519{uuid4().int % 10**8:08d}')
        command.upgrade(config, 'head')
        with engine.connect() as connection:
            return tuple(
                connection.execute(
                    text(
                        'SELECT status, failed_attempts, last_failed_attempt_on,'
                        ' blocked_at, closed_at FROM users WHERE uuid = :uuid'
                    ),
                    {'uuid': user_uuid},
                ).one()
            )
    finally:
        command.upgrade(config, 'head')
        _delete_user(engine, user_uuid)
        engine.dispose()


class TestUsersMigration:
    def test_moves_stored_cellphones_to_e164(self) -> None:
        old_cellphone = f'+51 9{uuid4().int % 10**8:08d}'

        stored = _stored_cellphone_after_upgrade(old_cellphone)

        assert stored == old_cellphone.replace(' ', '')

    def test_existing_users_become_active_without_failed_attempts(self) -> None:
        state = _account_state_after_upgrade()

        assert state == ('active', 0, None, None, None)
