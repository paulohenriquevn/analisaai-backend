"""create_dataset_columns_table

Revision ID: 02
Revises: 01
Create Date: 2025-03-14 12:00:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '02'
down_revision = '01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'data_processed',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['dataset_id'], ['datasets.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('dataset_id', 'name', name='unique_column_per_dataset')
    )


def downgrade() -> None:
    op.drop_table('data_processed')