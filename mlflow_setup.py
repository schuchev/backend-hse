import mlflow
from mlflow.sklearn import log_model
from model import train_model, save_model
import logging

logger = logging.getLogger(__name__)

MLFLOW_TRACKING_URI = "sqlite:///mlflow.db"
EXPERIMENT_NAME = "moderation-model"
MODEL_NAME = "moderation-model"


def register_model_in_mlflow():

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    mlflow.set_experiment(EXPERIMENT_NAME)

    logger.info("Starting model registration...")
    logger.info(f"Tracking URI: {MLFLOW_TRACKING_URI}")

    logger.info("Training model...")
    model = train_model()

    with mlflow.start_run():
        mlflow.log_param("model_type", "LogisticRegression")
        mlflow.log_param("features", "is_verified_seller, images_qty, description_length, category")

        logger.info(f"Registering model '{MODEL_NAME}'...")
        log_model(
            model,
            artifact_path="model",
            registered_model_name=MODEL_NAME
        )

        save_model(model, "model.pkl")

        logger.info(" Model registered successfully!")
        logger.info("Check MLflow UI at: http://localhost:5000")


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    try:
        register_model_in_mlflow()
        print(" Done!")
        print(" http://localhost:5000 ")
    except Exception as e:
        logger.error(f" Error: {e}", exc_info=True)
        sys.exit(1)
