"""
SHAPExplainer – wraps the `shap` library to produce per-feature
contribution explanations for each scoring dimension.
"""

from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING

import numpy as np
import shap

from src.core.feature_engine import FEATURE_NAMES
from src.models.schemas import SHAPExplanation

if TYPE_CHECKING:
    from src.core.scorer import EnsembleScorer

logger = logging.getLogger(__name__)


class SHAPExplainer:
    """
    Generates SHAP TreeExplainer values for the Random Forest ensemble.

    Usage
    -----
    >>> explainer = SHAPExplainer(scorer)
    >>> explanations = explainer.explain(feature_vector, category="Job")
    >>> for ex in explanations:
    ...     print(ex.dimension, ex.feature_contributions)
    """

    def __init__(self, scorer: EnsembleScorer) -> None:
        self._scorer = scorer
        # Cache SHAP TreeExplainers per model key.
        self._explainers: dict[tuple[str, str], shap.TreeExplainer] = {}
        logger.info("SHAPExplainer initialised  (shap==%s  numpy==%s)", shap.__version__, np.__version__)

    def explain(
        self,
        feature_vector: np.ndarray,
        category: str,
    ) -> list[SHAPExplanation]:
        """
        Return a ``SHAPExplanation`` for each of urgency / fit / importance.

        Parameters
        ----------
        feature_vector : 1-D numpy array of shape ``(n_features,)``.
        category       : One of ``"Admission"``, ``"Job"``, ``"Event"``, ``"Misc"``.
        """
        vec = feature_vector.reshape(1, -1)
        results: list[SHAPExplanation] = []

        logger.info("── SHAP explain  category=%-10s  n_features=%d ──", category, len(FEATURE_NAMES))

        for dim in ("urgency", "fit", "importance"):
            key = (category, dim)
            model = self._scorer.models.get(key) or self._scorer.models.get(("Misc", dim))

            if model is None:
                logger.warning("  [%s/%s] No model found — returning empty explanation", category, dim)
                results.append(SHAPExplanation(dimension=dim, base_value=5.0, feature_contributions={}))
                continue

            # Lazily build the TreeExplainer (cached per model key)
            if key not in self._explainers:
                self._explainers[key] = shap.TreeExplainer(model)
                logger.debug("  [%s/%s] Built new TreeExplainer", category, dim)

            exp = self._explainers[key]

            # ── Call shap_values ────────────────────────────────────────────
            try:
                shap_values = exp.shap_values(vec, check_additivity=False)
            except Exception as exc:
                logger.error(
                    "  [%s/%s] shap_values() raised: %s\n%s",
                    category, dim, exc, traceback.format_exc()
                )
                raise

            # ── Diagnose return shape (critical for cross-version compat) ───
            shap_arr = np.array(shap_values)
            logger.debug(
                "  [%s/%s] raw type=%-12s  np.array shape=%-20s  ndim=%d",
                category, dim,
                type(shap_values).__name__,
                str(shap_arr.shape),
                shap_arr.ndim,
            )

            # ── Normalise to 1-D contribution vector ────────────────────────
            # SHAP return shapes vary by version:
            #   Old (≤0.44) : ndarray (n_samples, n_features)           → 2-D
            #   New (≥0.45) : list or ndarray (n_outputs, n_samples, n_features) → 3-D
            if shap_arr.ndim == 3:
                contribs_1d = shap_arr[0, 0, :]
                logger.debug("  [%s/%s] 3-D → [0,0,:]  (SHAP ≥0.45 multi-output format)", category, dim)
            elif shap_arr.ndim == 2:
                contribs_1d = shap_arr[0, :]
                logger.debug("  [%s/%s] 2-D → [0,:]    (classic SHAP ≤0.44 format)", category, dim)
            elif shap_arr.ndim == 1:
                contribs_1d = shap_arr
                logger.debug("  [%s/%s] 1-D → already flat", category, dim)
            else:
                contribs_1d = shap_arr.flatten()
                logger.warning("  [%s/%s] Unexpected ndim=%d — flattening", category, dim, shap_arr.ndim)

            # ── Normalise expected_value to scalar ──────────────────────────
            ev = exp.expected_value
            base = float(np.asarray(ev).flat[0])
            logger.debug(
                "  [%s/%s] expected_value raw=%-20s  type=%-12s  → base=%.4f",
                category, dim, str(ev), type(ev).__name__, base,
            )

            # ── Build feature contributions dict ────────────────────────────
            contributions: dict[str, float] = {}
            for i, name in enumerate(FEATURE_NAMES):
                val = float(contribs_1d[i])
                if abs(val) > 1e-6:
                    contributions[name] = round(val, 4)

            # ── Log top-3 contributors ──────────────────────────────────────
            top3 = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:3]
            logger.info(
                "  ✅ [%s/%-10s]  base=%6.4f   top-3: %s",
                category, dim, base,
                " | ".join(f"{n}={v:+.4f}" for n, v in top3) or "—",
            )

            results.append(
                SHAPExplanation(
                    dimension=dim,
                    base_value=round(base, 4),
                    feature_contributions=contributions,
                )
            )

        logger.info("── SHAP complete: %d/3 dimensions computed ──", len(results))
        return results
