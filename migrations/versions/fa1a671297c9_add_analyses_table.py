"""add analyses table

Revision ID: fa1a671297c9
Revises: 405778c4ade1
Create Date: 2026-10-22 20:07:07.451008

The HNSW index on phishing_cases.embedding is created by hand in an earlier
migration and is not declared in the model, so autogenerate wants to drop it.
That drop was removed on purpose.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'fa1a671297c9'
down_revision: str | Sequence[str] | None = '405778c4ade1'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email_hash', sa.String(length=64), nullable=False),
        sa.Column('email_length', sa.Integer(), nullable=False),
        sa.Column('prompt_identifier', sa.String(length=100), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column(
            'hostnames', postgresql.ARRAY(sa.String(length=253)), nullable=False
        ),
        sa.Column(
            'cited_slugs', postgresql.ARRAY(sa.String(length=200)), nullable=False
        ),
        sa.Column('max_phishing_probability', sa.Float(), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_analyses_email_hash'), 'analyses', ['email_hash'], unique=False
    )
    op.create_index(
        op.f('ix_analyses_user_id'), 'analyses', ['user_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_analyses_user_id'), table_name='analyses')
    op.drop_index(op.f('ix_analyses_email_hash'), table_name='analyses')
    op.drop_table('analyses')
