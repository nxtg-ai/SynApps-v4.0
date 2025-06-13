"""Add completed_applets column to workflow_runs table

Revision ID: 8f25b9c4e9f4
Revises: 7a25b9c4e8f3
Create Date: 2025-06-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '8f25b9c4e9f4'
down_revision = '7a25b9c4e8f3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('workflow_runs', sa.Column('completed_applets', sa.JSON(), nullable=True))


def downgrade():
    op.drop_column('workflow_runs', 'completed_applets')
