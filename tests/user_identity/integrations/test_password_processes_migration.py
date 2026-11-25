from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text

from alembic import command
from app.migrations.handler import ALEMBIC_INI_PATH
from config.settings import settings

# The revision right before the password processes.
BEFORE_PASSWORD_PROCESSES = '989da0bd25c3'
STARTED_AT = datetime(2026, 11, 20, 15, 0, tzinfo=UTC)


@pytest.fixture
def engine() -> Iterator[Engine]:
    """The migrations run outside the test transaction; the database always ends at
    head, without the data the test wrote."""
    own_engine = create_engine(settings.database_url)
    yield own_engine
    command.upgrade(Config(str(ALEMBIC_INI_PATH)), 'head')
    own_engine.dispose()


def _insert_user(engine: Engine, user_uuid: UUID) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO users (uuid, first_name, last_name, cellphone,'
                ' created_at, updated_at, status, failed_attempts)'
                " VALUES (:uuid, 'rosa', 'quispe', :cellphone, :at, :at, 'active', 0)"
            ),
            {
                'uuid': user_uuid,
                'cellphone': f'+519{uuid4().int % 10**8:08d}',
                'at': STARTED_AT,
            },
        )


def _insert_process(
    engine: Engine, user_uuid: UUID, failure_reason: str = 'attempts'
) -> UUID:
    process_uuid = uuid4()
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO security_processes (uuid, user_uuid, type, status,'
                ' user_codes, support_codes, started_at, finished_at, failure_reason)'
                " VALUES (:uuid, :user_uuid, 'password_recovery', 'failed', 3, 0,"
                ' :at, :at, :failure_reason)'
            ),
            {
                'uuid': process_uuid,
                'user_uuid': user_uuid,
                'at': STARTED_AT,
                'failure_reason': failure_reason,
            },
        )
    return process_uuid


def _insert_event(engine: Engine, user_uuid: UUID, process_uuid: UUID) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                'INSERT INTO account_events (uuid, user_uuid, type, reason, actor,'
                ' created_at, process_uuid) VALUES (:uuid, :user_uuid,'
                " 'password_recovered', 'security_code', 'user', :at, :process_uuid)"
            ),
            {
                'uuid': uuid4(),
                'user_uuid': user_uuid,
                'at': STARTED_AT,
                'process_uuid': process_uuid,
            },
        )


def _process(engine: Engine, process_uuid: UUID, columns: str) -> tuple[Any, ...]:
    with engine.connect() as connection:
        return tuple(
            connection.execute(
                text(f'SELECT {columns} FROM security_processes WHERE uuid = :uuid'),
                {'uuid': process_uuid},
            ).one()
        )


def _events(engine: Engine, user_uuid: UUID) -> int:
    with engine.connect() as connection:
        return int(
            connection.execute(
                text('SELECT count(*) FROM account_events WHERE user_uuid = :uuid'),
                {'uuid': user_uuid},
            ).scalar_one()
        )


def _delete_user(engine: Engine, user_uuid: UUID) -> None:
    with engine.begin() as connection:
        for table in ('account_events', 'security_processes'):
            connection.execute(
                text(f'DELETE FROM {table} WHERE user_uuid = :uuid'),
                {'uuid': user_uuid},
            )
        connection.execute(
            text('DELETE FROM users WHERE uuid = :uuid'), {'uuid': user_uuid}
        )


class TestPasswordProcessesMigration:
    def test_existing_processes_start_without_password_rejections(
        self, engine: Engine
    ) -> None:
        config = Config(str(ALEMBIC_INI_PATH))
        user_uuid = uuid4()
        command.downgrade(config, BEFORE_PASSWORD_PROCESSES)
        try:
            _insert_user(engine, user_uuid)
            process_uuid = _insert_process(engine, user_uuid)

            command.upgrade(config, 'head')

            assert _process(engine, process_uuid, 'password_attempts') == (0,)
        finally:
            _delete_user(engine, user_uuid)

    def test_downgrading_keeps_the_processes_and_drops_the_new_events(
        self, engine: Engine
    ) -> None:
        config = Config(str(ALEMBIC_INI_PATH))
        user_uuid = uuid4()
        command.upgrade(config, 'head')
        try:
            _insert_user(engine, user_uuid)
            process_uuid = _insert_process(engine, user_uuid, 'password_attempts')
            _insert_event(engine, user_uuid, process_uuid)

            command.downgrade(config, BEFORE_PASSWORD_PROCESSES)

            assert _process(engine, process_uuid, 'failure_reason') == ('attempts',)
            assert _events(engine, user_uuid) == 0
        finally:
            command.upgrade(config, 'head')
            _delete_user(engine, user_uuid)
