"""
Pydantic v2 schemas for every stage of the email-processing pipeline.

Hierarchy
---------
RawEmailEnvelope  →  LLM  →  BaseEmailData (+ subtype)  →  FeatureVector
                                                          →  MLScores + SHAP
                                                          →  LinkTrust
                                                          ──► PipelineResult
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


# ──────────────────────────────────────────────────────────────────────
# User Profile & Site Analysis
# ──────────────────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    """The user's profile for deterministic requirement matching."""
    skills: list[str] = Field(default_factory=list)
    experience_level: Optional[str] = None
    education: Optional[str] = None
    location: Optional[str] = None
    interests: list[str] = Field(default_factory=list)


class RequirementStatus(BaseModel):
    """Result of analyzing a site against the user profile."""
    met: bool = Field(..., description="Whether the user meets the core requirements")
    met_requirements: list[str] = Field(default_factory=list, description="Requirements the user meets")
    missing_requirements: list[str] = Field(default_factory=list, description="Requirements the user is missing")


class SiteAnalysis(BaseModel):
    """Structured data extracted from a linked site."""
    summary: str = Field(..., description="Summary of the site content")
    extracted_requirements: list[str] = Field(default_factory=list, description="Requirements found on the page")
    match_status: Optional[RequirementStatus] = None


# ──────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────

class EmailType(str, enum.Enum):
    """Canonical email categories the LLM must choose from."""
    ADMISSION = "Admission"
    JOB = "Job"
    EVENT = "Event"
    MISC = "Misc"


# ──────────────────────────────────────────────────────────────────────
# Shared building blocks
# ──────────────────────────────────────────────────────────────────────

class NextStep(BaseModel):
    """A single actionable next-step recommended by the LLM."""
    action: str = Field(..., min_length=1, description="Concise action description")
    deadline: Optional[datetime] = Field(
        None,
        description="ISO-8601 deadline, if determinable from the email",
    )


class LinkMetadata(BaseModel):
    """Extracted hyperlink with context."""
    url: str = Field(..., description="Raw URL string from the email body")
    anchor_text: Optional[str] = Field(
        None, description="Visible anchor text, if any"
    )


# ──────────────────────────────────────────────────────────────────────
# Raw email envelope (pre-LLM)
# ──────────────────────────────────────────────────────────────────────

class RawEmailEnvelope(BaseModel):
    """Minimal structured data pulled straight from .eml headers + body."""
    message_id: Optional[str] = None
    subject: str = ""
    sender: str = ""
    recipients: list[str] = Field(default_factory=list)
    date: Optional[datetime] = None
    body_plain: str = ""
    body_html: str = ""
    links: list[LinkMetadata] = Field(default_factory=list)
    attachments: list[str] = Field(
        default_factory=list,
        description="Filenames of attachments",
    )


# ──────────────────────────────────────────────────────────────────────
# LLM-extracted data (post-validation)
# ──────────────────────────────────────────────────────────────────────

class BaseEmailData(BaseModel):
    """
    Common fields every email type must carry after LLM extraction.
    Subtypes add category-specific fields.
    """
    email_type: EmailType
    subject: str
    sender: str
    summary: str = Field(..., min_length=10, description="2-3 sentence summary")
    next_steps: list[NextStep] = Field(
        ..., min_length=1, max_length=3,
        description="1-3 concrete next actions",
    )
    key_dates: list[datetime] = Field(default_factory=list)
    links: list[LinkMetadata] = Field(default_factory=list)
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="LLM self-reported confidence in its extraction",
    )
    raw_llm_output: Optional[dict[str, Any]] = Field(
        None,
        description="Original LLM JSON for debugging / auditing",
    )


class AdmissionEmail(BaseEmailData):
    """Fields specific to university / programme admissions."""
    university: str = ""
    programme: str = ""
    application_deadline: Optional[datetime] = None
    requirements: list[str] = Field(default_factory=list)
    scholarship_mentioned: bool = False


class JobEmail(BaseEmailData):
    """Fields specific to job / internship offers."""
    company: str = ""
    role: str = ""
    location: Optional[str] = None
    salary_range: Optional[str] = None
    application_deadline: Optional[datetime] = None
    required_skills: list[str] = Field(default_factory=list)
    experience_level: Optional[str] = None


class EventEmail(BaseEmailData):
    """Fields specific to events, workshops, seminars."""
    event_name: str = ""
    organizer: Optional[str] = None
    event_date: Optional[datetime] = None
    venue: Optional[str] = None
    registration_link: Optional[str] = None
    is_virtual: bool = False


class MiscEmail(BaseEmailData):
    """Catch-all for emails that don't fit the other categories."""
    tags: list[str] = Field(default_factory=list)


# ──────────────────────────────────────────────────────────────────────
# ML scoring outputs
# ──────────────────────────────────────────────────────────────────────

class MLScores(BaseModel):
    """Urgency / Fit / Importance scores produced by the RF ensemble."""
    urgency: float = Field(..., ge=0.0, le=10.0)
    fit: float = Field(..., ge=0.0, le=10.0)
    importance: float = Field(..., ge=0.0, le=10.0)
    composite: float = Field(
        ..., ge=0.0, le=10.0,
        description="Weighted aggregate of the three scores",
    )


class SHAPExplanation(BaseModel):
    """Per-feature SHAP contributions for a single score dimension."""
    dimension: str = Field(..., description="'urgency' | 'fit' | 'importance'")
    base_value: float
    feature_contributions: dict[str, float] = Field(
        default_factory=dict,
        description="feature_name → SHAP value",
    )


# ──────────────────────────────────────────────────────────────────────
# Link trust
# ──────────────────────────────────────────────────────────────────────

class LinkTrust(BaseModel):
    """Trust assessment and optional content analysis for a URL."""
    url: str
    trust_score: float = Field(..., ge=1.0, le=10.0)
    reasons: list[str] = Field(default_factory=list)
    is_reachable: bool = True
    site_analysis: Optional[SiteAnalysis] = None


# ──────────────────────────────────────────────────────────────────────
# Unified pipeline result
# ──────────────────────────────────────────────────────────────────────

class PipelineResult(BaseModel):
    """
    The single JSON payload returned by the processing pipeline.
    This is the contract between the backend and the Streamlit frontend.
    """
    # ── identification
    source_file: str
    processed_at: datetime

    # ── extraction
    envelope: RawEmailEnvelope
    extracted_data: BaseEmailData
    next_steps: list[NextStep]

    # ── scoring
    scores: MLScores
    shap_explanations: list[SHAPExplanation] = Field(default_factory=list)

    # ── trust
    link_trust: list[LinkTrust] = Field(default_factory=list)

    # ── meta
    warnings: list[str] = Field(default_factory=list)
