# src.models – Pydantic schemas and ML artifact storage.

from .schemas import (
    EmailType,
    NextStep,
    BaseEmailData,
    AdmissionEmail,
    JobEmail,
    EventEmail,
    MiscEmail,
    MLScores,
    SHAPExplanation,
    LinkTrust,
    PipelineResult,
)

__all__ = [
    "EmailType",
    "NextStep",
    "BaseEmailData",
    "AdmissionEmail",
    "JobEmail",
    "EventEmail",
    "MiscEmail",
    "MLScores",
    "SHAPExplanation",
    "LinkTrust",
    "PipelineResult",
]
