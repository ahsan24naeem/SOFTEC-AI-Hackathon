"""
LLMExtractor – sends the raw email envelope to a Groq model and
validates the structured JSON response against Pydantic schemas.
"""

from __future__ import annotations

import json
import os
import textwrap
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from src.models.schemas import (
    AdmissionEmail,
    BaseEmailData,
    EmailType,
    EventEmail,
    JobEmail,
    MiscEmail,
    RawEmailEnvelope,
)

load_dotenv()

# ── System prompt (as specified) ──────────────────────────────────────

SYSTEM_PROMPT = textwrap.dedent("""\
    You are an expert email analyst. Given an email's subject, sender, date,
    and body, extract ALL relevant structured data into a single JSON object.

    RULES:
    1. Classify the email into exactly one type: Admission, Job, Event, or Misc.
    2. Always include a "next_steps" key – an array of 1-3 actionable items,
       each with an "action" (string) and an optional "deadline" (ISO-8601).
    3. Use ISO-8601 for every date/datetime field.
    4. No conversational filler – output ONLY valid JSON.
    5. Include a "confidence" field (0.0-1.0) indicating how confident you are.

    SCHEMA (fill in every key; use null for unknowns):
    {
      "email_type": "Admission", // Or "Job" | "Event" | "Misc"
      "subject": "...",
      "sender": "...",
      "summary": "2-3 sentence summary",
      "next_steps": [{"action": "...", "deadline": "ISO-8601 or null"}],
      "key_dates": ["ISO-8601", "..."],
      "links": [{"url": "...", "anchor_text": "..."}],
      "confidence": 0.95,

      // Admission-specific (include only if email_type == "Admission"):
      "university": "...",
      "programme": "...",
      "application_deadline": "ISO-8601 or null",
      "requirements": ["..."],
      "scholarship_mentioned": true,

      // Job-specific (include only if email_type == "Job"):
      "company": "...",
      "role": "...",
      "location": "...",
      "salary_range": "...",
      "application_deadline": "ISO-8601 or null",
      "required_skills": ["..."],
      "experience_level": "...",

      // Event-specific (include only if email_type == "Event"):
      "event_name": "...",
      "organizer": "...",
      "event_date": "ISO-8601 or null",
      "venue": "...",
      "registration_link": "...",
      "is_virtual": true,

      // Misc-specific (include only if email_type == "Misc"):
      "tags": ["..."]
    }
""")


# ── Type dispatch map ────────────────────────────────────────────────

_TYPE_MAP: dict[EmailType, type[BaseEmailData]] = {
    EmailType.ADMISSION: AdmissionEmail,
    EmailType.JOB: JobEmail,
    EmailType.EVENT: EventEmail,
    EmailType.MISC: MiscEmail,
}


class LLMExtractor:
    """
    Calls the Groq LLM to convert a `RawEmailEnvelope` into a
    validated, strongly-typed `BaseEmailData` subclass.
    """

    def __init__(
        self,
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError(
                "GROQ_API_KEY is not set. Copy .env.example → .env and fill it in."
            )

        self._model_name = model or os.getenv("LLM_MODEL", "llama-4-scout")
        self._temperature = temperature or float(
            os.getenv("LLM_TEMPERATURE", "0.1")
        )

        self._client = Groq(api_key=api_key)

    # ── public API ────────────────────────────────────────────────────

    def extract(self, envelope: RawEmailEnvelope) -> BaseEmailData:
        user_prompt = self._build_user_prompt(envelope)
        raw_json = self._call_llm(user_prompt)
        parsed = self._parse_json(raw_json)
        return self._validate(parsed)

    # ── internals ─────────────────────────────────────────────────────

    def _build_user_prompt(self, envelope: RawEmailEnvelope) -> str:
        parts = [
            f"Subject: {envelope.subject}",
            f"From: {envelope.sender}",
            f"Date: {envelope.date.isoformat() if envelope.date else 'N/A'}",
            f"Recipients: {', '.join(envelope.recipients) or 'N/A'}",
            "",
            "— Body (plain text) —",
            envelope.body_plain or "(no plain-text body)",
        ]

        if envelope.links:
            parts.append("\n— Links found in the email —")
            for lnk in envelope.links:
                label = f" [{lnk.anchor_text}]" if lnk.anchor_text else ""
                parts.append(f"  • {lnk.url}{label}")

        if envelope.attachments:
            parts.append("\n— Attachments —")
            for att in envelope.attachments:
                parts.append(f"  • {att}")

        return "\n".join(parts)

    def _call_llm(self, user_prompt: str) -> str:
        response = self._client.chat.completions.create(
            model=self._model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=self._temperature,
            response_format={"type": "json_object"},
        )
        return response.choices[0].message.content or "{}"

    @staticmethod
    def _parse_json(raw: str) -> dict[str, Any]:
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1]
            text = text.rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"LLM did not return valid JSON:\n{raw[:500]}") from exc

    @staticmethod
    def _validate(data: dict[str, Any]) -> BaseEmailData:
        raw_type = data.get("email_type", "Misc")
        try:
            email_type = EmailType(raw_type)
        except ValueError:
            email_type = EmailType.MISC
            data["email_type"] = email_type.value

        model_cls = _TYPE_MAP[email_type]
        data["raw_llm_output"] = data.copy()
        return model_cls.model_validate(data)
