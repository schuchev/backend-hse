import logging
from sklearn.linear_model import LogisticRegression
from schemas.predict import PredictRequest, PredictResponse

logger = logging.getLogger(__name__)


def normalize_features(request: PredictRequest) -> list[float]:
    """
    Преобразует входные данные в признаки для модели.

    Нормализация:
    - is_verified_seller: bool -> 1.0 или 0.0
    - images_qty: деление на 10
    - description_length: нормализуем делением на 1000
    - category:  деление на 100

    """
    is_verified = float(request.is_verified_seller)
    images_normalized = request.images_qty / 10.0
    description_length_normalized = len(request.description) / 1000.0
    category_normalized = request.category / 100.0

    features = [
        is_verified,
        images_normalized,
        description_length_normalized,
        category_normalized
    ]


    return features


def predict_violation(request: PredictRequest,model: LogisticRegression) -> PredictResponse:
    """
    Предсказывает, есть ли нарушение в объявлении.

    """
    if model is None:
        raise ValueError("Model is not available")

    features = normalize_features(request)

    features_array = [[f for f in features]]

    prediction = int(model.predict(features_array)[0])
    probabilities = model.predict_proba(features_array)[0]

    probability = float(probabilities[1])

    response = PredictResponse(
        is_violation=bool(prediction),
        probability=probability
    )

    logger.info(
        "Prediction for seller_id=%d, item_id=%d: "
        "is_violation=%s, probability=%.4f",
        request.seller_id,
        request.item_id,
        response.is_violation,
        response.probability
    )

    return response
