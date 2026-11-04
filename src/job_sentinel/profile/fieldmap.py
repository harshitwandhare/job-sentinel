"""
profile/fieldmap.py
───────────────────
What the filler learned, so the same unknown question is not asked twice.

The answer bank holds the answers. This holds the **wording**: when a form asks
something the bank does not recognise, and the user says which stored answer it
means, that pairing is written here and the next form phrased the same way is
answered without asking.

Two decisions worth keeping:

* **A mapping points at a field id, never at a value.** Copying answers into a
  second file would put personal data somewhere the user does not expect it,
  and would go stale the moment the bank is edited.
* **Mappings are scoped to the ATS that asked.** Workday and Greenhouse use the
  same words for different questions often enough that a global map is a way to
  answer the wrong one. A lookup falls back to the shared ``any`` scope, which
  is where a user puts a wording they are confident about everywhere.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import yaml
from pydantic import BaseModel, Field

from job_sentinel.profile.answers import normalise

__all__ = [
    "DEFAULT_FIELDMAP_PATH",
    "FieldMap",
    "LearnedLabel",
    "load_fieldmap",
    "save_fieldmap",
]

_REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_FIELDMAP_PATH = _REPO_ROOT / "data" / "fieldmap.yaml"

#: Scope used when a mapping should apply on every board.
ANY_ATS = "any"


class LearnedLabel(BaseModel):
    """One form wording, paired with the answer-bank field it means.

    Attributes
    ----------
    label:
        The visible label as the form wrote it, kept verbatim so the user can
        recognise what they taught. Lookups use its normalised form.
    field_id:
        The ``AnswerField.id`` this wording asks for.
    ats:
        Which board asked, or ``"any"``.
    uses:
        How often it has been applied since being learned. A wording that never
        comes up again is a candidate for pruning.
    learned:
        ISO date it was first recorded.
    """

    label: str
    field_id: str
    ats: str = ANY_ATS
    uses: int = 0
    learned: str = ""

    @property
    def key(self) -> str:
        """The normalised wording this entry is looked up by."""
        return normalise(self.label)


class FieldMap(BaseModel):
    """Every wording the filler has been taught."""

    version: int = 1
    labels: list[LearnedLabel] = Field(default_factory=list)

    def resolve(self, label: str, ats: str = ANY_ATS) -> str | None:
        """The field id this wording means on *ats*, or None.

        The board's own scope wins over the shared one, so a wording taught for
        Workday is not overruled by a general mapping.
        """
        text = normalise(label)
        if not text:
            return None
        fallback: str | None = None
        for entry in self.labels:
            if entry.key != text:
                continue
            if entry.ats == ats:
                return entry.field_id
            if entry.ats == ANY_ATS:
                fallback = entry.field_id
        return fallback

    def learn(self, label: str, field_id: str, ats: str = ANY_ATS) -> LearnedLabel:
        """Record that *label* on *ats* means *field_id*.

        Re-teaching the same wording updates it in place rather than stacking
        entries, so correcting a mistake is one call and the file does not grow
        a history of wrong answers.
        """
        text = normalise(label)
        for entry in self.labels:
            if entry.key == text and entry.ats == ats:
                entry.label = label
                entry.field_id = field_id
                return entry
        entry = LearnedLabel(
            label=label,
            field_id=field_id,
            ats=ats,
            learned=datetime.now(tz=UTC).date().isoformat(),
        )
        self.labels.append(entry)
        return entry

    def forget(self, label: str, ats: str = ANY_ATS) -> bool:
        """Drop a wording. True when something was removed."""
        text = normalise(label)
        before = len(self.labels)
        self.labels = [e for e in self.labels if not (e.key == text and e.ats == ats)]
        return len(self.labels) < before

    def record_use(self, label: str, ats: str = ANY_ATS) -> None:
        """Count one application of this wording, for pruning later."""
        text = normalise(label)
        for entry in self.labels:
            if entry.key == text and entry.ats in (ats, ANY_ATS):
                entry.uses += 1
                return


def load_fieldmap(path: Path | None = None) -> FieldMap:
    """Load the learned map, returning an empty one when the file is absent."""
    path = path or DEFAULT_FIELDMAP_PATH
    if not path.is_file():
        return FieldMap()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return FieldMap.model_validate(data)


def save_fieldmap(fieldmap: FieldMap, path: Path | None = None) -> Path:
    """Write the learned map, creating the directory if needed."""
    path = path or DEFAULT_FIELDMAP_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(fieldmap.model_dump(), sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )
    return path
