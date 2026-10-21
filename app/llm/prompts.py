"""Load versioned prompt files stored in the repository."""

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from string import Template
from typing import Final

PROMPTS_DIRECTORY: Final[Path] = Path(__file__).resolve().parents[2] / "prompts"


class PromptNotFoundError(RuntimeError):
    """Raised when a prompt name or version has no files on disk."""


@dataclass(frozen=True)
class PromptTemplate:
    """A system prompt plus a user message template, at one version."""

    name: str
    version: str
    system: str
    user: Template

    @property
    def identifier(self) -> str:
        """Value stored with each analysis, e.g. ``explain_email/v1``."""
        return f"{self.name}/{self.version}"

    def render_user(self, **values: str) -> str:
        """Fill the user template; a missing value raises instead of passing."""
        return self.user.substitute(**values)


@cache
def load_prompt(name: str, version: str) -> PromptTemplate:
    """Read a prompt version from disk.

    ``name`` and ``version`` must be constants in the code, never request data.

    Raises:
        PromptNotFoundError: If the version directory or a file is missing.
    """
    directory = PROMPTS_DIRECTORY / name / version
    try:
        system = (directory / "system.md").read_text(encoding="utf-8").strip()
        user = (directory / "user.md").read_text(encoding="utf-8").strip()
    except FileNotFoundError as error:
        raise PromptNotFoundError(
            f"Prompt {name}/{version} not found in {directory}"
        ) from error
    return PromptTemplate(
        name=name,
        version=version,
        system=system,
        user=Template(user),
    )
