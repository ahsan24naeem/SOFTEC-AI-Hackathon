"""
EmailController – façade that the Streamlit frontend (or any consumer)
calls to process emails through the full pipeline.

This is the **only public entry point** into the backend.  The frontend
should never import from ``src.core`` directly.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from src.core.explainer import SHAPExplainer
from src.core.extractor import LLMExtractor
from src.core.feature_engine import FeatureTransformer
from src.core.link_checker import LinkChecker
from src.core.parser import EMLParser
from src.core.scorer import EnsembleScorer
from src.models.schemas import PipelineResult, UserProfile

logger = logging.getLogger(__name__)


class EmailController:
    """
    Orchestrates:
        EMLParser → LLMExtractor → FeatureTransformer → EnsembleScorer
                                                       → SHAPExplainer
                                                       → LinkChecker
                                                       ──► PipelineResult

    Usage
    -----
    >>> ctrl = EmailController()
    >>> result = ctrl.process("data/raw_eml/sample.eml")
    >>> print(result.model_dump_json(indent=2))
    """

    def __init__(
        self,
        *,
        enable_link_probe: bool = False,
        model: str | None = None,
        temperature: float | None = None,
    ) -> None:
        """
        Parameters
        ----------
        enable_link_probe : Pass through to ``LinkChecker``.
        model             : Override the Gemini model name.
        temperature       : Override the LLM temperature.
        """
        self._extractor = LLMExtractor(model=model, temperature=temperature)
        self._scorer = EnsembleScorer()
        self._explainer = SHAPExplainer(self._scorer)
        self._link_checker = LinkChecker(enable_http_probe=enable_link_probe)

    # ── public API ────────────────────────────────────────────────────

    def process(
        self, eml_path: str | Path, user_profile: Optional[UserProfile] = None
    ) -> PipelineResult:
        """
        End-to-end: .eml file → unified ``PipelineResult`` JSON payload.

        Raises
        ------
        FileNotFoundError : If the ``.eml`` path doesn't exist.
        ValueError        : If the LLM output is unparsable / invalid.
        EnvironmentError  : If ``GROQ_API_KEY`` is unset.
        """
        warnings: list[str] = []
        eml_path = Path(eml_path)

        # 1 ── Parse raw .eml
        logger.info("Parsing %s", eml_path)
        envelope = EMLParser.parse(eml_path)

        # 2 ── LLM extraction
        logger.info("Extracting structured data via LLM…")
        extracted = self._extractor.extract(envelope, user_profile=user_profile)

        # 3 ── Feature engineering
        feature_vec = FeatureTransformer.transform(extracted, envelope)

        # 4 ── ML scoring
        logger.info("Scoring with RF ensemble…")
        scores = self._scorer.score(extracted, envelope, user_profile=user_profile)

        # 5 ── SHAP explainability
        logger.info("Computing SHAP explanations…")
        try:
            shap_explanations = self._explainer.explain(
                feature_vec, extracted.email_type.value
            )
        except Exception as exc:
            logger.warning("SHAP failed: %s", exc)
            shap_explanations = []
            warnings.append(f"SHAP explanations unavailable: {exc}")

        # 6 ── Link trust
        logger.info("Checking %d links…", len(extracted.links))
        link_trust = self._link_checker.check(extracted.links, user_profile=user_profile)

        # 7 ── Assemble result
        return PipelineResult(
            source_file=str(eml_path),
            processed_at=datetime.now(timezone.utc),
            envelope=envelope,
            extracted_data=extracted,
            next_steps=extracted.next_steps,
            scores=scores,
            shap_explanations=shap_explanations,
            link_trust=link_trust,
            warnings=warnings,
        )

    # ── convenience ───────────────────────────────────────────────────

    def process_many(
        self, eml_paths: list[str | Path], user_profile: Optional[UserProfile] = None
    ) -> list[PipelineResult]:
        """Process a batch of .eml files sequentially."""
        return [self.process(p, user_profile) for p in eml_paths]
