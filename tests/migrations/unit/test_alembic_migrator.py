from collections.abc import Callable
from pathlib import Path

import pytest
from sqlalchemy.exc import OperationalError

from app.migrations import alembic_migrator
from app.migrations.alembic_migrator import (
    DATABASE_NOT_READY_MESSAGE,
    AlembicMigrator,
    DatabaseNotReadyError,
)

INI_PATH = Path('alembic.ini')


def _failing_upgrade(error: Exception) -> Callable[[object, str], None]:
    def upgrade(config: object, revision: str) -> None:
        raise error

    return upgrade


class TestAlembicMigrator:
    def test_reports_a_clear_error_when_the_database_is_not_ready(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        error = OperationalError(
            'SELECT 1', {}, Exception('database "turfbook_identity_dev" does not exist')
        )
        monkeypatch.setattr(alembic_migrator, 'upgrade', _failing_upgrade(error))

        with pytest.raises(DatabaseNotReadyError) as raised:
            AlembicMigrator(INI_PATH).upgrade()

        assert str(raised.value).startswith(DATABASE_NOT_READY_MESSAGE)
        assert 'turfbook_identity_dev' in str(raised.value)

    def test_lets_other_errors_pass_through(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(
            alembic_migrator, 'upgrade', _failing_upgrade(RuntimeError('bad revision'))
        )

        with pytest.raises(RuntimeError, match='bad revision'):
            AlembicMigrator(INI_PATH).upgrade()
