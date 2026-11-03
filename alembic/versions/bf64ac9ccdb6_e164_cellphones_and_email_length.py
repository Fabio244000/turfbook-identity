"""e164 cellphones and email length

Revision ID: bf64ac9ccdb6
Revises: 526c4e04b55e
Create Date: 2026-11-03 13:44:25.851179

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bf64ac9ccdb6'
down_revision: Union[str, Sequence[str], None] = '526c4e04b55e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Stored cellphones move to E.164 (`+51 9…` → `+519…`) before the column shrinks,
    # or the shorter column would reject them.
    op.execute(
        "UPDATE users SET cellphone = replace(cellphone, ' ', '') "
        "WHERE cellphone LIKE '+51 %'"
    )
    op.alter_column('users', 'cellphone',
               existing_type=sa.VARCHAR(length=13),
               type_=sa.String(length=12),
               existing_nullable=False)
    op.alter_column('users', 'email',
               existing_type=sa.VARCHAR(length=250),
               type_=sa.String(length=254),
               existing_nullable=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'email',
               existing_type=sa.String(length=254),
               type_=sa.VARCHAR(length=250),
               existing_nullable=True)
    # The column widens before the space comes back, or `+51 9…` would not fit.
    op.alter_column('users', 'cellphone',
               existing_type=sa.String(length=12),
               type_=sa.VARCHAR(length=13),
               existing_nullable=False)
    op.execute(
        "UPDATE users SET cellphone = '+51 ' || substr(cellphone, 4) "
        "WHERE cellphone LIKE '+519%' AND length(cellphone) = 12"
    )
