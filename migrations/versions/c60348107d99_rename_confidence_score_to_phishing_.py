"""rename confidence_score to phishing_probability

Revision ID: c60348107d99
Revises: 1163bea9354c
Create Date: 2026-07-29 11:12:37.899873

"""

from collections.abc import Sequence

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "c60348107d99"
down_revision: str | Sequence[str] | None = "1163bea9354c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "predictions",
        "confidence_score",
        new_column_name="phishing_probability",
    )


def downgrade() -> None:
    op.alter_column(
        "predictions",
        "phishing_probability",
        new_column_name="confidence_score",
    )
