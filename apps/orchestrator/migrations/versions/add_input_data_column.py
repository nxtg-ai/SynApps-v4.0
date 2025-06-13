"""Add input_data column to workflow_runs table

Revision ID: 7a25b9c4e8f3
Revises: 81751dea8da7
Create Date: 2025-06-08 09:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7a25b9c4e8f3'
down_revision = '81751dea8da7'
branch_labels = None
depends_on = None


def upgrade():
    # Add input_data column to workflow_runs table
    op.add_column('workflow_runs', sa.Column('input_data', sa.JSON(), nullable=True))


def downgrade():
    # Remove input_data column from workflow_runs table
    op.drop_column('workflow_runs', 'input_data')
