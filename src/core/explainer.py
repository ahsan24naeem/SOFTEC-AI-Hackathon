"""
SHAPExplainer – wraps the `shap` library to produce per-feature
contribution explanations for each scoring dimension.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import shap

from src.core.feature_engine import FEATURE_NAMES
from src.models.schemas import SHAPExplanation

if TYPE_CHECKING:
    from src.core.scorer import EnsembleScorer


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

    def explain(
        self,
        feature_vector: np.ndarray,
        category: str,
    ) -> list[SHAPExplanation]:
        """
        Return a `SHAPExplanation` for each of urgency / fit / importance.

        Parameters
        ----------
        feature_vector : 1-D numpy array of shape ``(n_features,)``.
        category       : One of ``"Admission"``, ``"Job"``, ``"Event"``, ``"Misc"``.
        """
        vec = feature_vector.reshape(1, -1)
        results: list[SHAPExplanation] = []

        for dim in ("urgency", "fit", "importance"):
            key = (category, dim)
            model = self._scorer.models.get(key) or self._scorer.models.get(
                ("Misc", dim)
            )
            if model is None:
                results.append(
                    SHAPExplanation(
                        dimension=dim,
                        base_value=5.0,
                        feature_contributions={},
                    )
                )
                continue

            # Lazily build the TreeExplainer.
            if key not in self._explainers:
                self._explainers[key] = shap.TreeExplainer(model)

            exp = self._explainers[key]
            shap_values = exp.shap_values(vec, check_additivity=False)

            # ── Normalise shap_values to a 1-D array of length n_features ──
            # SHAP return shapes vary by version:
            #   • Old (≤0.44): ndarray shape (n_samples, n_features)
            #   • New (≥0.45): list of arrays OR ndarray (n_outputs, n_samples, n_features)
            shap_arr = np.array(shap_values)
            if shap_arr.ndim == 3:
                # (n_outputs, n_samples, n_features) → take first output, first sample
                contribs_1d = shap_arr[0, 0, :]
            elif shap_arr.ndim == 2:
                # (n_samples, n_features) → take first sample
                contribs_1d = shap_arr[0, :]
            elif shap_arr.ndim == 1:
                # Already 1-D (n_features,)
                contribs_1d = shap_arr
            else:
                contribs_1d = shap_arr.flatten()

            # ── Normalise expected_value to a Python float ──────────────────
            # Some SHAP versions return an ndarray for expected_value
            ev = exp.expected_value
            base = float(np.asarray(ev).flat[0])

            contributions: dict[str, float] = {}
            for i, name in enumerate(FEATURE_NAMES):
                val = float(contribs_1d[i])
                if abs(val) > 1e-6:  # only include non-trivial contributions
                    contributions[name] = round(val, 4)

            results.append(
                SHAPExplanation(
                    dimension=dim,
                    base_value=round(base, 4),
                    feature_contributions=contributions,
                )
            )

        return results
