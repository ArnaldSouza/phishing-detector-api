"""add phishing_cases table with pgvector

Revision ID: 405778c4ade1
Revises: 6a9ccfba5b9b
Create Date: 2026-10-20 13:45:42.810328

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = '405778c4ade1'
down_revision: str | Sequence[str] | None = '6a9ccfba5b9b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('phishing_cases',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('slug', sa.String(length=200), nullable=False),
    sa.Column('title', sa.String(length=200), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('slug')
    )

    op.execute(
        "CREATE INDEX ix_phishing_cases_embedding "
        "ON phishing_cases USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_phishing_cases_embedding")
    op.drop_table('phishing_cases')