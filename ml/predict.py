import os
import json
import math
from typing import List, Dict, Any, Tuple

# Path to the exported model parameters
MODEL_FILE_PATH = os.path.join(os.path.dirname(__file__), "models", "transaction_classifier.json")

# Default fallback weights if model parameters fail to load
DEFAULT_CENTROIDS = {
    "Safe": [0.0096, 0.0031, 0.1111, 0.1111],
    "Suspicious": [0.0888, 0.0831, 0.3333, 0.5185],
    "High Risk": [0.6231, 0.6031, 0.7777, 0.9259]
}

DEFAULT_BOUNDS = {
    "amount": [300.0, 490000.0],
    "location_drift": [0.5, 4500.0],
    "velocity_1h": [1.0, 10.0],
    "device_score": [0.05, 0.95]
}


class ModelLoader:
    """Singleton pattern to load and cache classifier weights."""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelLoader, cls).__new__(cls)
            cls._instance.load_model()
        return cls._instance
        
    def load_model(self) -> None:
        try:
            if os.path.exists(MODEL_FILE_PATH):
                with open(MODEL_FILE_PATH, "r") as f:
                    data = json.load(f)
                    self.centroids = data["centroids"]
                    self.bounds = data["bounds"]
                    self.loaded = True
            else:
                self.centroids = DEFAULT_CENTROIDS
                self.bounds = DEFAULT_BOUNDS
                self.loaded = False
        except Exception:
            self.centroids = DEFAULT_CENTROIDS
            self.bounds = DEFAULT_BOUNDS
            self.loaded = False


def _euclidean_distance(v1: List[float], v2: List[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(v1, v2)))


def predict_transaction_risk(
    amount: float, 
    location_drift: float, 
    velocity_1h: int, 
    device_score: float
) -> Tuple[str, float]:
    """
    Ingests live metrics, normalizes them, and runs Nearest Centroid inference.
    Returns: Tuple of (classification: Safe/Suspicious/High Risk, ml_score: 0.0 - 100.0)
    """
    model = ModelLoader()
    
    # 1. Normalize live values using MinMax bounds
    features = []
    inputs = {
        "amount": amount,
        "location_drift": location_drift,
        "velocity_1h": float(velocity_1h),
        "device_score": device_score
    }
    
    for key in ["amount", "location_drift", "velocity_1h", "device_score"]:
        val = inputs[key]
        f_min, f_max = model.bounds[key]
        norm_val = (val - f_min) / (f_max - f_min) if f_max > f_min else 0.0
        # Clip to [0.0, 1.0] boundary
        norm_val = max(0.0, min(1.0, norm_val))
        features.append(float(norm_val))
        
    # 2. Compute Euclidean distance from each centroid
    distances = {}
    best_status = "Safe"
    min_dist = float("inf")
    
    for status, centroid in model.centroids.items():
        dist = _euclidean_distance(features, centroid)
        distances[status] = dist
        if dist < min_dist:
            min_dist = dist
            best_status = status
            
    # 3. Calculate dynamic ML probability score (0.0 to 100.0)
    safe_dist = distances.get("Safe", 1.0)
    high_risk_dist = distances.get("High Risk", 1.0)
    total = safe_dist + high_risk_dist
    
    if total == 0:
        ml_score = 50.0
    else:
        ml_score = (safe_dist / total) * 100.0
        
    return best_status, float(ml_score)
