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
            shap_values = exp.shap_values(vec)  # shape (1, n_features)
            base = float(exp.expected_value)

            contributions: dict[str, float] = {}
            for i, name in enumerate(FEATURE_NAMES):
                val = float(shap_values[0, i])
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
