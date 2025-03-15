"""create_data_processed_table

Revision ID: 01
Revises: 
Create Date: 2025-03-16 00:00:00

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON

# revision identifiers, used by Alembic.
revision = '01'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'data_processed',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('dataset_id', sa.String(), nullable=False),
        sa.Column('preprocessing_config', JSON, nullable=True),
        sa.Column('feature_engineering_config', JSON, nullable=True),
        sa.Column('validation_results', JSON, nullable=True),
        sa.Column('missing_values_report', JSON, nullable=True),
        sa.Column('outliers_report', JSON, nullable=True),
        sa.Column('feature_importance', JSON, nullable=True),
        sa.Column('transformations_applied', JSON, nullable=True),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('data_processed')