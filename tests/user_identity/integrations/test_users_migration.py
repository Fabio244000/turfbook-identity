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
BEFORE_TIMESTAMPTZ = '5cc507fe9ed1'
# Stored without zone before the migration, in UTC (how the app always wrote them).
CREATED_AT_UTC = datetime(2026, 11, 3, 15, 0)
UPDATED_AT_UTC = datetime(2026, 11, 3, 16, 30)
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


def _insert_user_with_state(
    engine: Engine, user_uuid: UUID, created_at: datetime, updated_at: datetime
) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone,'
                ' created_at, updated_at, status, failed_attempts)'
                " VALUES (:uuid, 'rosa', 'quispe', :cellphone, :created_at,"
                " :updated_at, 'active', 0)"
            ),
            {
                'uuid': user_uuid,
                'cellphone': f'+519{uuid4().int % 10**8:08d}',
                'created_at': created_at,
                'updated_at': updated_at,
            },
        )


def _timestamps(engine: Engine, user_uuid: UUID) -> tuple[Any, ...]:
    with engine.connect() as connection:
        return tuple(
            connection.execute(
                text('SELECT created_at, updated_at FROM users WHERE uuid = :uuid'),
                {'uuid': user_uuid},
            ).one()
        )


def _go_to(config: Config, revision: str) -> None:
    command.upgrade(config, 'head')
    if revision != 'head':
        command.downgrade(config, revision)


def _timestamps_across(
    from_revision: str, to_revision: str, **stored: datetime
) -> tuple[Any, ...]:
    """Inserts a user at `from_revision`, migrates to `to_revision` and returns its
    timestamps; the database always ends at head, without the user."""
    config = Config(str(ALEMBIC_INIT_PATH))
    engine = create_engine(settings.database_url)
    user_uuid = uuid4()
    _go_to(config, from_revision)
    try:
        _insert_user_with_state(engine, user_uuid, **stored)
        _go_to(config, to_revision)
        return _timestamps(engine, user_uuid)
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

    def test_timestamps_keep_their_instant_when_they_gain_a_zone(self) -> None:
        stored = _timestamps_across(
            BEFORE_TIMESTAMPTZ,
            'head',
            created_at=CREATED_AT_UTC,
            updated_at=UPDATED_AT_UTC,
        )

        assert stored == (
            CREATED_AT_UTC.replace(tzinfo=UTC),
            UPDATED_AT_UTC.replace(tzinfo=UTC),
        )

    def test_downgrading_keeps_the_instant_as_utc_without_zone(self) -> None:
        stored = _timestamps_across(
            'head',
            BEFORE_TIMESTAMPTZ,
            created_at=CREATED_AT_UTC.replace(tzinfo=UTC),
            updated_at=UPDATED_AT_UTC.replace(tzinfo=UTC),
        )

        assert stored == (CREATED_AT_UTC, UPDATED_AT_UTC)
