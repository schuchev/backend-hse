from __future__ import annotations

import logging
from typing import Optional

from sklearn.linear_model import LogisticRegression

from schemas.predict import PredictRequest

logger = logging.getLogger(__name__)


class ModelNotAvailableError(RuntimeError):
    """Ошибка когда нет модели"""


class ModerationPredictor:

    _instance: Optional["ModerationPredictor"] = None

    def __init__(self, model: LogisticRegression):
        self._model = model

    @classmethod
    def init(cls, model: LogisticRegression) -> None:
        cls._instance = ModerationPredictor(model)

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    @classmethod
    def instance(cls) -> "ModerationPredictor":
        if cls._instance is None:
            raise ModelNotAvailableError("Model is not available")
        return cls._instance

    @staticmethod
    def _normalize_features(request: PredictRequest) -> list[float]:
        is_verified = float(request.is_verified_seller)
        images_normalized = request.images_qty / 10.0
        description_length_normalized = len(request.description) / 1000.0
        category_normalized = request.category / 100.0

        return [
            is_verified,
            images_normalized,
            description_length_normalized,
            category_normalized,
        ]

    def predict_proba_violation(self, request: PredictRequest) -> float:

        features = self._normalize_features(request)
        x = [features]

        proba = float(self._model.predict_proba(x)[0][1])
        return proba
