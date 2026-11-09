"""users timestamps with time zone

Revision ID: 1faf587c3cc7
Revises: 5cc507fe9ed1
Create Date: 2026-11-09 16:38:48.994865

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1faf587c3cc7'
down_revision: Union[str, Sequence[str], None] = '5cc507fe9ed1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Stored without zone, always in UTC (the app writes UTC): read them as UTC
    # explicitly, so the result never depends on the server's TimeZone setting.
    for column in ('created_at', 'updated_at'):
        op.alter_column(
            'users',
            column,
            existing_type=postgresql.TIMESTAMP(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Downgrade schema."""
    # Back to UTC without zone, the form the app stored before.
    for column in ('updated_at', 'created_at'):
        op.alter_column(
            'users',
            column,
            existing_type=sa.DateTime(timezone=True),
            type_=postgresql.TIMESTAMP(),
            existing_nullable=False,
            postgresql_using=f"{column} AT TIME ZONE 'UTC'",
        )
