"""merge_heads

Revision ID: e69c629d5500
Revises: 3201bb1d2a40, 8f25b9c4e9f4
Create Date: 2025-06-08 12:18:36.585670

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e69c629d5500'
down_revision: Union[str, None] = ('3201bb1d2a40', '8f25b9c4e9f4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
