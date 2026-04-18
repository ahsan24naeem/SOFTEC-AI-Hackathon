"""
EnsembleScorer – a suite of Random Forest Regressors (3 per email category)
that score Urgency, Fit, and Importance on a 0-10 scale.

In production these models are loaded from `.pkl` files under
`src/models/artifacts/`. For the hackathon bootstrap, this module can
generate synthetic training data, train the forests, and persist them.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd
from groq import Groq
from sklearn.ensemble import RandomForestRegressor

from src.core.feature_engine import FEATURE_NAMES, FeatureTransformer
from src.models.schemas import BaseEmailData, EmailType, MLScores, RawEmailEnvelope

# Where serialised models live.
_ARTIFACTS_DIR = Path(__file__).resolve().parent.parent / "models" / "artifacts"

# Scoring dimensions.
DIMENSIONS = ("urgency", "fit", "importance")

# One ensemble per (category, dimension).
_ModelKey = tuple[str, str]  # (category_value, dimension)


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
        self._load_or_train()

        api_key = os.getenv("GROQ_API_KEY")
        self._llm_client = Groq(api_key=api_key) if api_key else None
        self._model_name = os.getenv("LLM_MODEL", "llama-4-scout")

    # ── public API ────────────────────────────────────────────────────

    def score(
        self,
        extracted: BaseEmailData,
        envelope: RawEmailEnvelope,
    ) -> MLScores:
        """
        Run the feature vector through the matching category's forests
        and return `MLScores`.
        """
        vec = FeatureTransformer.transform(extracted, envelope).reshape(1, -1)
        cat = extracted.email_type.value

        results: dict[str, float] = {}
        for dim in DIMENSIONS:
            key: _ModelKey = (cat, dim)
            # Fall back to Misc models if a specific category wasn't trained.
            model = self._models.get(key) or self._models.get(("Misc", dim))
            if model is None:
                results[dim] = 5.0  # neutral default
            else:
                raw = float(model.predict(vec)[0])
                results[dim] = round(np.clip(raw, 0.0, 10.0), 2)

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
            if not getattr(self, "_llm_client", None):
                # Fallback to empty if LLM is not initialized (e.g. during very first startup tests)
                return
            
            df = self._generate_llm_data()
            df.to_csv(data_file, index=False)

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
