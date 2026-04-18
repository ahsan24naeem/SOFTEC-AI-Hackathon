"""
FeatureTransformer – converts a validated `BaseEmailData` (+ envelope)
into a flat numerical vector suitable for scikit-learn models.

Feature list (deterministic, no LLM calls):
  0  type_is_admission
  1  type_is_job
  2  type_is_event
  3  type_is_misc
  4  subject_length
  5  body_length
  6  next_steps_count
  7  key_dates_count
  8  links_count
  9  attachments_count
 10  has_deadline
 11  confidence
 12  days_until_deadline   (0 if no deadline)
 13  has_salary_info
 14  required_skills_count
 15  is_virtual
 16  scholarship_mentioned
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import numpy as np

from src.models.schemas import (
    AdmissionEmail,
    BaseEmailData,
    EmailType,
    EventEmail,
    JobEmail,
    RawEmailEnvelope,
)

# Canonical feature order (matches the docstring above).
FEATURE_NAMES: list[str] = [
    "type_is_admission",
    "type_is_job",
    "type_is_event",
    "type_is_misc",
    "subject_length",
    "body_length",
    "next_steps_count",
    "key_dates_count",
    "links_count",
    "attachments_count",
    "has_deadline",
    "confidence",
    "days_until_deadline",
    "has_salary_info",
    "required_skills_count",
    "is_virtual",
    "scholarship_mentioned",
]


class FeatureTransformer:
    """
    Stateless transformer: `BaseEmailData` + `RawEmailEnvelope` → 1-D numpy
    array of shape `(len(FEATURE_NAMES),)`.

    Usage
    -----
    >>> vec = FeatureTransformer.transform(extracted, envelope)
    >>> vec.shape
    (17,)
    """

    @staticmethod
    def transform(
        extracted: BaseEmailData,
        envelope: RawEmailEnvelope,
    ) -> np.ndarray:
        """Return a 1-D float64 feature vector."""
        feats: dict[str, float] = {}

        # One-hot email type
        feats["type_is_admission"] = float(extracted.email_type == EmailType.ADMISSION)
        feats["type_is_job"]       = float(extracted.email_type == EmailType.JOB)
        feats["type_is_event"]     = float(extracted.email_type == EmailType.EVENT)
        feats["type_is_misc"]      = float(extracted.email_type == EmailType.MISC)

        # Text lengths
        feats["subject_length"] = float(len(envelope.subject))
        feats["body_length"]    = float(len(envelope.body_plain))

        # Counts
        feats["next_steps_count"] = float(len(extracted.next_steps))
        feats["key_dates_count"]  = float(len(extracted.key_dates))
        feats["links_count"]      = float(len(extracted.links))
        feats["attachments_count"] = float(len(envelope.attachments))

        # Deadline proximity
        deadline = FeatureTransformer._find_earliest_deadline(extracted)
        feats["has_deadline"] = float(deadline is not None)
        if deadline:
            now = datetime.now(timezone.utc)
            delta = (deadline - now).total_seconds() / 86_400  # days
            feats["days_until_deadline"] = max(delta, 0.0)
        else:
            feats["days_until_deadline"] = 0.0

        # Confidence
        feats["confidence"] = extracted.confidence

        # Category-specific signals
        feats["has_salary_info"] = 0.0
        feats["required_skills_count"] = 0.0
        feats["is_virtual"] = 0.0
        feats["scholarship_mentioned"] = 0.0

        if isinstance(extracted, JobEmail):
            feats["has_salary_info"] = float(bool(extracted.salary_range))
            feats["required_skills_count"] = float(len(extracted.required_skills))
        elif isinstance(extracted, EventEmail):
            feats["is_virtual"] = float(extracted.is_virtual)
        elif isinstance(extracted, AdmissionEmail):
            feats["scholarship_mentioned"] = float(extracted.scholarship_mentioned)

        # Assemble in canonical order
        return np.array(
            [feats[name] for name in FEATURE_NAMES],
            dtype=np.float64,
        )

    @staticmethod
    def feature_names() -> list[str]:
        """Return the ordered list of feature names."""
        return list(FEATURE_NAMES)

    # ── helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _find_earliest_deadline(extracted: BaseEmailData) -> datetime | None:
        """
        Search through next_steps deadlines and key_dates to find the
        earliest future datetime.
        """
        now = datetime.now(timezone.utc)
        candidates: list[datetime] = []

        for step in extracted.next_steps:
            if step.deadline and step.deadline > now:
                candidates.append(step.deadline)

        for dt in extracted.key_dates:
            if dt > now:
                candidates.append(dt)

        # Check subtype-specific deadlines
        if hasattr(extracted, "application_deadline") and extracted.application_deadline:
            if extracted.application_deadline > now:
                candidates.append(extracted.application_deadline)
        if hasattr(extracted, "event_date") and extracted.event_date:
            if extracted.event_date > now:
                candidates.append(extracted.event_date)

        return min(candidates) if candidates else None
