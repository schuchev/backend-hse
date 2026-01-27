from schemas.predict import PredictRequest

def predict_listing(request: PredictRequest) -> bool:
    """
    Предсказывает, одобрено ли объявление.

    Правила:
    - Подтверждённые продавцы: объявление всегда одобрено
    - Неподтверждённые продавцы: одобрено только если есть изображения

    Args:
        request: Данные объявления

    Returns:
        True если объявление одобрено, False иначе
    """
    if request.is_verified_seller:
        return True

    return request.images_qty > 0