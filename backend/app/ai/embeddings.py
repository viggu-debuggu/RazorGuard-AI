import threading
from typing import List
from app.core.config import settings
from app.core.logging import logger

class EmbeddingEngine:
    """Thread-safe singleton class loading SentenceTransformer locally."""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EmbeddingEngine, cls).__new__(cls)
                cls._instance.initialized = False
        return cls._instance

    def initialize(self) -> None:
        if self.initialized:
            return
        try:
            # pyrefly: ignore [missing-import]
            from sentence_transformers import SentenceTransformer
            logger.info("loading_embedding_model", model_name=settings.EMBEDDING_MODEL_NAME)
            self.model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
            self.initialized = True
            logger.info("embedding_model_loaded_successfully")
        except Exception as e:
            logger.error("embedding_model_load_failed", error=str(e))
            self.initialized = False

    def get_embedding(self, text: str) -> List[float]:
        self.initialize()
        if not self.initialized:
            # Fallback to zero vector of size 384 if model isn't loaded
            return [0.0] * 384
        try:
            embedding = self.model.encode(text)
            return [float(val) for val in embedding]
        except Exception as e:
            logger.error("embedding_generation_failed", error=str(e))
            return [0.0] * 384


def generate_embedding(text: str) -> List[float]:
    """Exposed convenience function to generate dense text embeddings."""
    return EmbeddingEngine().get_embedding(text)
