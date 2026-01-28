import numpy as np
import pickle
import logging
import os
from sklearn.linear_model import LogisticRegression
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_PATH = "model.pkl"


def train_model() -> LogisticRegression:

    logger.info("Training model on synthetic data...")

    np.random.seed(42)
    X = np.random.rand(1000, 4)
    y = (X[:, 0] < 0.3) & (X[:, 1] < 0.2)
    y = y.astype(int)

    model = LogisticRegression()
    model.fit(X, y)

    logger.info("Model trained successfully")
    return model


def save_model(model: LogisticRegression, path: str = MODEL_PATH) -> None:

    try:
        with open(path, "wb") as f:
            pickle.dump(model, f)
        logger.info("Model saved successfully to %s", path)
    except Exception as e:
        logger.error("Failed to save model: %s", e)
        raise


def load_model(path: str = MODEL_PATH) -> LogisticRegression:

    try:
        with open(path, "rb") as f:
            model = pickle.load(f)
        logger.info("Model loaded successfully from %s", path)
        return model
    except FileNotFoundError:
        logger.warning("Model file not found at %s", path)
        raise


def load_or_train_model(path: str = MODEL_PATH) -> LogisticRegression:

    try:
        return load_model(path)
    except FileNotFoundError:
        logger.info("Model not found, training new model...")
        model = train_model()
        save_model(model, path)
        return model



def load_model_from_mlflow(model_name: str = "moderation-model",stage: str = "Production") -> LogisticRegression:

    try:
        import mlflow

        model_uri = f"models:/{model_name}/{stage}"
        logger.info("Loading model from MLflow: %s", model_uri)

        model = mlflow.sklearn.load_model(model_uri)

        logger.info(" Model loaded successfully from MLflow")
        return model
    except Exception as e:
        logger.error("Failed to load model from MLflow: %s", e)
        raise


def load_model_smart(use_mlflow: bool = False) -> LogisticRegression:

    if use_mlflow:
        try:
            logger.info("Attempting to load model from MLflow...")
            return load_model_from_mlflow()
        except Exception as e:
            logger.warning(
                "Failed to load from MLflow, falling back to local file: %s", e
            )
            return load_or_train_model()
    else:
        logger.info("Loading model from local file...")
        return load_or_train_model()