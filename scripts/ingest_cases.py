"""Load the knowledge base cases into PostgreSQL with their embeddings.

Run from the project root:
    uv run python -m scripts.ingest_cases
"""

from pathlib import Path
from typing import Final

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import PhishingCase
from app.rag.embeddings import DOCUMENT_TASK, embed_texts

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
CASES_DIRECTORY: Final[Path] = PROJECT_ROOT / "knowledge" / "cases"
TITLE_PREFIX: Final[str] = "# "


class InvalidCaseError(ValueError):
    """Raised when a case file does not follow the expected format."""


def parse_case(path: Path) -> tuple[str, str, str]:
    """Read a case file and return its slug, title and full content.

    Args:
        path: Markdown file whose first line is a ``# Title`` heading.

    Raises:
        InvalidCaseError: If the file is empty or has no title line.
    """
    content = path.read_text(encoding="utf-8").strip()
    first_line = content.splitlines()[0] if content else ""

    if not first_line.startswith(TITLE_PREFIX):
        raise InvalidCaseError(f"{path.name}: first line must start with '# '")

    return path.stem, first_line.removeprefix(TITLE_PREFIX).strip(), content


def load_cases(directory: Path) -> list[tuple[str, str, str]]:
    """Parse every markdown case in a directory, in a stable order."""
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise InvalidCaseError(f"No case files found in {directory}")
    return [parse_case(path) for path in paths]


def upsert_cases(
    session: Session,
    cases: list[tuple[str, str, str]],
    embeddings: list[list[float]],
) -> tuple[int, int]:
    """Insert new cases and update existing ones, matched by slug.

    Returns:
        A tuple with the number of created and updated rows.
    """
    existing = {
        case.slug: case for case in session.scalars(select(PhishingCase)).all()
    }
    created = updated = 0

    for (slug, title, content), embedding in zip(cases, embeddings, strict=True):
        record = existing.get(slug)
        if record is None:
            session.add(
                PhishingCase(
                    slug=slug, title=title, content=content, embedding=embedding
                )
            )
            created += 1
        else:
            record.title = title
            record.content = content
            record.embedding = embedding
            updated += 1

    session.commit()
    return created, updated


def main() -> None:
    cases = load_cases(CASES_DIRECTORY)
    print(f"parsed {len(cases)} cases")

    embeddings = embed_texts([content for _, _, content in cases], DOCUMENT_TASK)
    print(f"generated {len(embeddings)} embeddings")

    with SessionLocal() as session:
        created, updated = upsert_cases(session, cases, embeddings)
    print(f"created: {created} | updated: {updated}")


if __name__ == "__main__":
    main()