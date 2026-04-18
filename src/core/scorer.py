"""
EnsembleScorer – a suite of Random Forest Regressors (3 per email category)
that score Urgency, Fit, and Importance on a 0-10 scale.

In production these models are loaded from `.pkl` files under
`src/models/artifacts/`. For the hackathon bootstrap, this module can
generate synthetic training data, train the forests, and persist them.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from groq import Groq
from sklearn.ensemble import RandomForestRegressor

from src.core.feature_engine import FEATURE_NAMES, FeatureTransformer
from src.models.schemas import (
    AdmissionEmail,
    BaseEmailData,
    EmailType,
    JobEmail,
    MLScores,
    RawEmailEnvelope,
    UserProfile,
)

# Where serialised models live.
_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "models" / "artifacts"

# Scoring dimensions.
DIMENSIONS = ("urgency", "fit", "importance")

# One ensemble per (category, dimension).
_ModelKey = tuple[str, str]  # (category_value, dimension)

logger = logging.getLogger(__name__)


class EnsembleScorer:
    """
    Manages an ensemble of Random Forest regressors.

    Layout:
        3 categories  ×  3 dimensions  =  9 models total
        (Misc shares the "Event" models as a fallback.)

    Usage
    -----
    >>> scorer = EnsembleScorer()          # loads or trains models
    >>> scores = scorer.score(extracted, envelope)
    >>> print(scores.urgency, scores.fit, scores.importance)
    """

    def __init__(self, artifacts_dir: str | Path | None = None) -> None:
        self._dir = Path(artifacts_dir) if artifacts_dir else _ARTIFACTS_DIR
        self._dir.mkdir(parents=True, exist_ok=True)
        self._data_dir = self._dir.parent.parent.parent / "data" / "synthetic"
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._models: dict[_ModelKey, RandomForestRegressor] = {}
        api_key = os.getenv("GROQ_API_KEY")
        self._llm_client = Groq(api_key=api_key) if api_key else None
        self._model_name = os.getenv("LLM_MODEL", "llama-4-scout")
        self._load_or_train()

    # ── public API ────────────────────────────────────────────────────

    def score(
        self,
        extracted: BaseEmailData,
        envelope: RawEmailEnvelope,
        user_profile: Optional[UserProfile] = None,
    ) -> MLScores:
        """
        Run the feature vector through the matching category's forests
        and return `MLScores`.

        A deterministic post-processing layer then adjusts:
        - fit: based on user profile matching
        - importance: based on extraction completeness
        """
        vec = FeatureTransformer.transform(extracted, envelope).reshape(1, -1)
        feat_map = {
            name: float(value)
            for name, value in zip(FEATURE_NAMES, vec[0].tolist())
        }
        cat = extracted.email_type.value

        results: dict[str, float] = {}
        missing_dims: list[str] = []
        for dim in DIMENSIONS:
            key: _ModelKey = (cat, dim)
            # Fall back to Misc models if a specific category wasn't trained.
            model = self._models.get(key) or self._models.get(("Misc", dim))
            if model is None:
                missing_dims.append(dim)
                results[dim] = self._heuristic_dimension_score(dim, feat_map)
            else:
                raw = float(model.predict(vec)[0])
                results[dim] = round(np.clip(raw, 0.0, 10.0), 4)

        if missing_dims:
            logger.warning(
                "Using heuristic fallback for missing model(s): %s",
                ", ".join(missing_dims),
            )

        results = self._apply_deterministic_adjustments(
            results,
            extracted,
            user_profile=user_profile,
        )

        composite = round(
            0.40 * results["urgency"]
            + 0.35 * results["importance"]
            + 0.25 * results["fit"],
            2,
        )
        composite = min(composite, 10.0)

        return MLScores(
            urgency=results["urgency"],
            fit=results["fit"],
            importance=results["importance"],
            composite=composite,
        )

    # ── deterministic adjustment layer ───────────────────────────────

    def _apply_deterministic_adjustments(
        self,
        base_scores: dict[str, float],
        extracted: BaseEmailData,
        *,
        user_profile: Optional[UserProfile],
    ) -> dict[str, float]:
        adjusted = dict(base_scores)

        completeness = self._completeness_score(extracted)
        adjusted["importance"] = round(
            self._clamp(0.75 * adjusted["importance"] + 0.25 * completeness),
            4,
        )

        if user_profile is not None:
            fit_delta = self._profile_fit_adjustment(extracted, user_profile)
            adjusted["fit"] = round(self._clamp(adjusted["fit"] + fit_delta), 4)

        return adjusted

    @staticmethod
    def _clamp(value: float) -> float:
        return float(np.clip(value, 0.0, 10.0))

    @staticmethod
    def _is_present(value: object) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, tuple, set, dict)):
            return len(value) > 0
        return True

    def _completeness_score(self, extracted: BaseEmailData) -> float:
        required_documents = getattr(extracted, "required_documents", [])
        contact_info = getattr(extracted, "contact_info", [])

        checks: list[bool] = [
            self._is_present(extracted.summary),
            len(extracted.next_steps) > 0,
            len(extracted.key_dates) > 0,
            len(extracted.links) > 0,
            len(required_documents) > 0,
            len(contact_info) > 0,
            self._is_present(getattr(extracted, "application_deadline", None))
            or self._is_present(getattr(extracted, "event_date", None)),
        ]

        if isinstance(extracted, AdmissionEmail):
            checks.append(len(extracted.requirements) > 0)
        if isinstance(extracted, JobEmail):
            checks.append(len(extracted.required_skills) > 0)

        completeness = 10.0 * (sum(1 for ok in checks if ok) / len(checks))
        return round(completeness, 4)

    def _profile_fit_adjustment(
        self,
        extracted: BaseEmailData,
        user_profile: UserProfile,
    ) -> float:
        boost = 0.0

        preferred_types = {
            item.strip().lower()
            for item in user_profile.preferred_opportunity_types
            if item and item.strip()
        }
        if preferred_types:
            if extracted.email_type.value.lower() in preferred_types:
                boost += 1.2
            else:
                boost -= 0.2

        required_skills = {
            item.strip().lower()
            for item in getattr(extracted, "required_skills", [])
            if item and item.strip()
        }
        profile_skills = {
            item.strip().lower()
            for item in user_profile.skills
            if item and item.strip()
        }
        if required_skills and profile_skills:
            overlap = len(required_skills & profile_skills)
            missing = len(required_skills - profile_skills)
            boost += min(1.5, overlap * 0.45)
            boost -= min(0.9, missing * 0.12)

        pref_location = (user_profile.location_preference or user_profile.location or "").strip().lower()
        email_location = (
            getattr(extracted, "location", None)
            or getattr(extracted, "venue", None)
            or ""
        ).strip().lower()
        if pref_location and email_location:
            if pref_location in email_location or email_location in pref_location:
                boost += 0.5
            elif "remote" in pref_location and "remote" in email_location:
                boost += 0.5
            else:
                boost -= 0.25

        if isinstance(extracted, AdmissionEmail) and user_profile.cgpa is not None:
            threshold = self._extract_cgpa_threshold(extracted.requirements)
            if threshold is not None:
                if user_profile.cgpa >= threshold:
                    boost += 0.7
                else:
                    boost -= 1.0

        financial_need = (user_profile.financial_need or "").strip().lower()
        if financial_need and financial_need != "none":
            if getattr(extracted, "scholarship_mentioned", False):
                boost += 0.4
            if isinstance(extracted, JobEmail) and getattr(extracted, "salary_range", None):
                boost += 0.3

        if user_profile.past_experience and getattr(extracted, "experience_level", None):
            boost += 0.2

        return float(np.clip(boost, -2.5, 2.5))

    @staticmethod
    def _extract_cgpa_threshold(requirements: list[str]) -> Optional[float]:
        pattern = re.compile(r"(?:cgpa|gpa)[^0-9]{0,16}([0-4](?:\.\d{1,2})?)", re.IGNORECASE)
        for req in requirements:
            match = pattern.search(req)
            if match:
                value = float(match.group(1))
                if 0.0 <= value <= 4.0:
                    return value
        return None

    @staticmethod
    def _heuristic_dimension_score(
        dimension: str,
        feats: dict[str, float],
    ) -> float:
        has_deadline = feats.get("has_deadline", 0.0)
        days = feats.get("days_until_deadline", 0.0)
        confidence = feats.get("confidence", 0.5)
        next_steps = feats.get("next_steps_count", 0.0)
        key_dates = feats.get("key_dates_count", 0.0)
        links = feats.get("links_count", 0.0)
        attachments = feats.get("attachments_count", 0.0)
        req_skills = feats.get("required_skills_count", 0.0)
        scholarship = feats.get("scholarship_mentioned", 0.0)
        salary_info = feats.get("has_salary_info", 0.0)

        deadline_pressure = max(0.0, min(1.0, (14.0 - days) / 14.0)) if has_deadline else 0.0

        if dimension == "urgency":
            score = (
                2.5
                + 3.0 * has_deadline
                + 2.8 * deadline_pressure
                + 0.3 * key_dates
                + 0.2 * next_steps
            )
        elif dimension == "fit":
            score = (
                2.0
                + 4.0 * confidence
                + 0.35 * req_skills
                + 0.8 * scholarship
                + 0.4 * salary_info
            )
        else:  # importance
            score = (
                2.0
                + 0.5 * has_deadline
                + 0.35 * next_steps
                + 0.35 * key_dates
                + 0.22 * links
                + 0.12 * attachments
                + 2.2 * confidence
            )

        return round(float(np.clip(score, 0.0, 10.0)), 4)

    @property
    def models(self) -> dict[_ModelKey, RandomForestRegressor]:
        """Expose internal model dict (used by SHAPExplainer)."""
        return self._models

    # ── persistence ───────────────────────────────────────────────────

    def _model_path(self, cat: str, dim: str) -> Path:
        return self._dir / f"rf_{cat.lower()}_{dim}.pkl"

    def _load_or_train(self) -> None:
        """Try loading persisted models; if any are missing, train all."""
        all_found = True
        for cat in ("Admission", "Job", "Event", "Misc"):
            for dim in DIMENSIONS:
                p = self._model_path(cat, dim)
                if p.exists():
                    self._models[(cat, dim)] = joblib.load(p)
                else:
                    all_found = False

        if not all_found:
            self._train_synthetic()

    # ── LLM-generated synthetic training ─────────────────────────────

    def _train_synthetic(self) -> None:
        """
        Generate synthetic feature vectors using an LLM and train one RF per
        (category, dimension). The LLM creates realistic samples which are
        persisted to disk.
        """
        data_file = self._data_dir / "llm_synthetic_data.csv"
        
        if data_file.exists():
            df = pd.read_csv(data_file)
        else:
            if self._llm_client:
                df = self._generate_llm_data()
            else:
                logger.warning("GROQ_API_KEY missing for synthetic model generation; using bootstrap dataset.")
                df = pd.DataFrame()

            if df.empty:
                df = self._generate_bootstrap_data()

            df.to_csv(data_file, index=False)

        # Ensure expected columns exist even if upstream data is partial.
        for col in [*FEATURE_NAMES, *DIMENSIONS]:
            if col not in df.columns:
                df[col] = 0.0

        for cat in ("Admission", "Job", "Event", "Misc"):
            cat_df = df[df[f"type_is_{cat.lower()}"] == 1.0].copy()
            if cat_df.empty:
                continue
            
            X = cat_df[FEATURE_NAMES].values
            for dim in DIMENSIONS:
                y = cat_df[dim].values
                model = RandomForestRegressor(
                    n_estimators=50,
                    max_depth=6,
                    random_state=42,
                    n_jobs=-1,
                )
                model.fit(X, y)
                self._models[(cat, dim)] = model
                joblib.dump(model, self._model_path(cat, dim))

    def _generate_bootstrap_data(self, rows_per_category: int = 100) -> pd.DataFrame:
        """Create deterministic fallback training data when LLM generation is unavailable."""
        rng = np.random.default_rng(42)
        rows: list[dict[str, float]] = []

        categories = ["Admission", "Job", "Event", "Misc"]
        for cat in categories:
            for _ in range(rows_per_category):
                row = {name: 0.0 for name in FEATURE_NAMES}

                row["type_is_admission"] = float(cat == "Admission")
                row["type_is_job"] = float(cat == "Job")
                row["type_is_event"] = float(cat == "Event")
                row["type_is_misc"] = float(cat == "Misc")

                row["subject_length"] = float(rng.integers(12, 140))
                row["body_length"] = float(rng.integers(120, 5000))
                row["next_steps_count"] = float(rng.integers(1, 4))
                row["key_dates_count"] = float(rng.integers(0, 4))
                row["links_count"] = float(rng.integers(0, 8))
                row["attachments_count"] = float(rng.integers(0, 3))

                has_deadline = float(rng.random() < 0.68)
                row["has_deadline"] = has_deadline
                row["confidence"] = float(rng.uniform(0.55, 0.97))
                row["days_until_deadline"] = float(rng.uniform(0, 60)) if has_deadline else 0.0

                row["has_salary_info"] = float(cat == "Job" and rng.random() < 0.6)
                row["required_skills_count"] = float(rng.integers(2, 9) if cat == "Job" else rng.integers(0, 3))
                row["is_virtual"] = float(cat == "Event" and rng.random() < 0.55)
                row["scholarship_mentioned"] = float(cat == "Admission" and rng.random() < 0.6)

                deadline_pressure = max(0.0, min(1.0, (14.0 - row["days_until_deadline"]) / 14.0)) if has_deadline else 0.0
                urgency = (
                    2.2
                    + 3.0 * has_deadline
                    + 3.0 * deadline_pressure
                    + 0.2 * row["key_dates_count"]
                    + float(rng.normal(0, 0.4))
                )
                fit = (
                    2.0
                    + 4.1 * row["confidence"]
                    + 0.3 * row["required_skills_count"]
                    + 0.7 * row["scholarship_mentioned"]
                    + 0.4 * row["has_salary_info"]
                    + float(rng.normal(0, 0.35))
                )
                importance = (
                    2.0
                    + 0.35 * row["next_steps_count"]
                    + 0.3 * row["key_dates_count"]
                    + 0.2 * row["links_count"]
                    + 1.0 * has_deadline
                    + 2.0 * row["confidence"]
                    + float(rng.normal(0, 0.4))
                )

                row["urgency"] = float(np.clip(urgency, 0.0, 10.0))
                row["fit"] = float(np.clip(fit, 0.0, 10.0))
                row["importance"] = float(np.clip(importance, 0.0, 10.0))
                rows.append(row)

        return pd.DataFrame(rows)

    def _generate_llm_data(self) -> pd.DataFrame:
        """
        Call the Groq LLM to generate 200 realistic rows (50 per category) 
        of feature vectors and target scores.
        """
        rows = []
        for cat in ("Admission", "Job", "Event", "Misc"):
            prompt = f"""
            Generate 50 realistic feature vectors for an email classifier and target scores for the '{cat}' category.
            Output ONLY a JSON object containing a "data" array.
            Each item in the array must be an object with these exact keys (values must be numeric):
            
            FEATURES (use sensible realism based on the category):
            "type_is_admission" (0 or 1), "type_is_job" (0 or 1), "type_is_event" (0 or 1), "type_is_misc" (0 or 1),
            "subject_length" (int 10-150), "body_length" (int 50-5000), "next_steps_count" (int 0-5),
            "key_dates_count" (int 0-5), "links_count" (int 0-10), "attachments_count" (int 0-5),
            "has_deadline" (0.0 or 1.0), "confidence" (float 0.5-1.0), "days_until_deadline" (float 0.0-60.0),
            "has_salary_info" (0.0 or 1.0), "required_skills_count" (int 0-10), "is_virtual" (0.0 or 1.0),
            "scholarship_mentioned" (0.0 or 1.0)
            
            TARGETS (float 0.0-10.0, use heuristics: urgency is high when days_until_deadline is low, fit is high when confidence/skills match):
            "urgency", "fit", "importance"
            
            Ensure type_is_{cat.lower()} is 1 and other types are 0.
            """
            try:
                response = self._llm_client.chat.completions.create(
                    model=self._model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    response_format={"type": "json_object"},
                )
                raw = response.choices[0].message.content
                data = json.loads(raw).get("data", [])
                rows.extend(data)
            except Exception as e:
                print(f"Dataset generation failed for {cat}: {e}")
                
        return pd.DataFrame(rows)
