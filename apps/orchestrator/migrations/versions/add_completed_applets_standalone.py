"""Add completed_applets column to workflow_runs table (standalone)

Revision ID: 9f25b9c4e9f5
Revises: e69c629d5500
Create Date: 2025-06-08

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f25b9c4e9f5'
down_revision = 'e69c629d5500'  # This is the merge revision
branch_labels = None
depends_on = None


def upgrade():
    # Check if the column already exists to avoid errors
    try:
        op.add_column('workflow_runs', sa.Column('completed_applets', sa.JSON(), nullable=True))
        print("Successfully added completed_applets column to workflow_runs table")
    except Exception as e:
        print(f"Error adding column (it might already exist): {e}")
        # Continue with migration even if column exists


def downgrade():
    try:
        op.drop_column('workflow_runs', 'completed_applets')
    except Exception as e:
        print(f"Error dropping column: {e}")
