"""
profile/answers.py
──────────────────
The answer bank: every question an application form asks, answered once.

Application forms ask the same thirty questions in slightly different words.
Typing them again per application is where the time goes, and where mistakes
get made on the questions that matter most.

Matching is on the **visible label text**, not on a CSS selector. Workday
tenants ship very different DOM for identical questions, so "Are you legally
authorized to work in the United States?" is stable where ``#input-7`` is not.
A field matches when any of its ``match`` phrases appears in the normalised
label, longest phrase first so a specific question beats a general one.

Two things this file deliberately does not hold:

* **Secrets.** No passwords, no GPA, no street address. Fields the user must
  answer in person are listed in ``private`` and the filler skips them.
* **Judgement.** ``never_claim`` records what must not go on an application.
  It exists so the resume routing and any generated free text can be checked
  against it, not so anything is auto-approved.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

__all__ = [
    "DEFAULT_ANSWERS_PATH",
    "AnswerBank",
    "AnswerField",
    "FieldKind",
    "contains_phrase",
    "example_answers",
    "load_answers",
    "save_answers",
]

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_ANSWERS_PATH = _REPO_ROOT / "data" / "answers.yaml"

#: Dropped outright rather than turned into a space, so "U.S." normalises to
#: "us" and "bachelor's" to "bachelors". Replacing them would give "u s" and
#: "bachelor s", and a phrase like "us citizen" would then never match.
#: Written by codepoint: a literal curly apostrophe here is indistinguishable
#: from a straight one when reading the source.
_ELIDE = {ord(c): None for c in (".", "'", chr(0x2019), chr(0x00B4), "`")}
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")


def normalise(label: str) -> str:
    """Lower-case a form label and strip punctuation so phrases match reliably.

    Form labels carry asterisks, colons, non-breaking spaces and stray markup,
    none of which should decide whether a question is recognised.
    """
    folded = label.casefold().translate(_ELIDE)
    return _SPACE.sub(" ", _PUNCT.sub(" ", folded)).strip()


def contains_phrase(haystack: str, needle: str) -> bool:
    """True when *needle* appears in *haystack* on whole-word boundaries.

    Plain substring matching is wrong for short tokens: a rule written to catch
    "ai" would also fire on "chair" and "said", quietly routing the wrong
    resume. Both arguments are expected to be normalised already.
    """
    if not needle:
        return False
    return re.search(rf"(?<![a-z0-9]){re.escape(needle)}(?![a-z0-9])", haystack) is not None


class FieldKind(StrEnum):
    """How the browser filler should enter a value."""

    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    DATE = "date"
    FILE = "file"


class AnswerField(BaseModel):
    """One question and its settled answer.

    Attributes
    ----------
    id:
        Stable slug, used in logs and by the learned field map.
    match:
        Phrases to look for in a normalised label. Any one matching is enough.
    kind:
        How to enter it.
    value:
        The answer. ``None`` means the user answers it in person.
    options:
        For a select or radio, acceptable option texts in order of preference,
        so the filler can pick the closest one a given form actually offers.
    note:
        Why the answer is what it is. Shown in the overlay, never submitted.
    """

    id: str
    match: list[str] = Field(default_factory=list)
    kind: FieldKind = FieldKind.TEXT
    value: str | None = None
    options: list[str] = Field(default_factory=list)
    note: str = ""

    @property
    def answerable(self) -> bool:
        """True when this field carries a value the filler may enter."""
        return self.value is not None and self.value != ""


class AnswerBank(BaseModel):
    """Every stored answer, plus the rules that govern using them."""

    version: int = 1
    updated: str = ""
    #: Where ``resume_routing`` paths are relative to. Kept here rather than in
    #: settings because it only means anything alongside the routing it serves,
    #: and a resume library usually lives outside this repository.
    resume_root: str = ""
    fields: list[AnswerField] = Field(default_factory=list)
    private: list[str] = Field(default_factory=list)
    resume_routing: list[dict[str, Any]] = Field(default_factory=list)
    never_claim: list[str] = Field(default_factory=list)

    # ── Lookup ────────────────────────────────────────────────────────────────

    def find(self, label: str) -> AnswerField | None:
        """Return the field whose phrasing best fits *label*, or None.

        The longest matching phrase wins, so "are you a us citizen or permanent
        resident" does not get answered by a field matching the bare word
        "citizen".
        """
        text = normalise(label)
        if not text:
            return None

        best: tuple[int, AnswerField] | None = None
        for field in self.fields:
            for phrase in field.match:
                needle = normalise(phrase)
                if contains_phrase(text, needle) and (best is None or len(needle) > best[0]):
                    best = (len(needle), field)
        return best[1] if best else None

    def is_private(self, field_id: str) -> bool:
        """True when this field must be left for the user to answer."""
        return field_id in self.private

    def resume_for(self, job_title: str) -> str | None:
        """Return the resume path whose routing rule matches *job_title*."""
        text = normalise(job_title)
        for rule in self.resume_routing:
            triggers = rule.get("match", [])
            if any(contains_phrase(text, normalise(str(t))) for t in triggers):
                return str(rule.get("file", "")) or None
        return None

    def resume_path_for(self, job_title: str) -> Path | None:
        """The routed resume as a path on disk, when ``resume_root`` is set.

        Returns None when nothing routes or no root is configured, so the
        caller can say "pick one yourself" instead of inventing a location.
        """
        picked = self.resume_for(job_title)
        if not picked or not self.resume_root:
            return None
        return Path(self.resume_root).expanduser() / picked


# ── Persistence ───────────────────────────────────────────────────────────────


def load_answers(path: Path | None = None) -> AnswerBank:
    """Load the answer bank, returning an empty one when the file is absent."""
    path = path or DEFAULT_ANSWERS_PATH
    if not path.is_file():
        return AnswerBank()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return AnswerBank.model_validate(data)


def example_answers() -> AnswerBank:
    """A small, realistic bank to seed a new install.

    Placeholders only. Mirrors :func:`job_sentinel.profile.store.example_profile`
    so ``answers init`` has something to write that is obviously meant to be
    edited rather than submitted.
    """
    return AnswerBank(
        version=1,
        updated="",
        fields=[
            AnswerField(
                id="legal_name",
                match=["legal name", "full legal name"],
                kind=FieldKind.TEXT,
                value="Your Full Name",
            ),
            AnswerField(
                id="email",
                match=["email address", "email"],
                kind=FieldKind.TEXT,
                value="you@example.edu",
                note="Use the same address on the resume, the form and any referral email.",
            ),
            AnswerField(
                id="authorized_to_work",
                match=["legally authorized to work", "are you authorized to work"],
                kind=FieldKind.RADIO,
                value="Yes",
                options=["Yes", "No"],
            ),
            AnswerField(
                id="requires_sponsorship",
                match=["require sponsorship", "now or in the future require sponsorship"],
                kind=FieldKind.RADIO,
                value=None,
                note="Answer honestly. The form's certification covers this one.",
            ),
            AnswerField(
                id="gpa",
                match=["gpa", "grade point average"],
                kind=FieldKind.TEXT,
                value=None,
                note="Left blank on purpose. Read it off your transcript, never guess.",
            ),
        ],
        private=["gpa", "requires_sponsorship"],
        resume_routing=[
            {"match": ["software engineer", "sde"], "file": "resumes/swe.pdf"},
            {"match": ["machine learning", "ai"], "file": "resumes/ai-ml.pdf"},
        ],
    )


def save_answers(bank: AnswerBank, path: Path | None = None) -> Path:
    """Write the answer bank as block-style YAML. Returns the path."""
    path = path or DEFAULT_ANSWERS_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(
            bank.model_dump(mode="json"),
            sort_keys=False,
            allow_unicode=True,
            default_flow_style=False,
        ),
        encoding="utf-8",
    )
    return path
