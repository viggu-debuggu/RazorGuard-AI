import os
import json
import math
from typing import List, Dict, Any, Tuple
from ml.preprocess import prepare_dataset

class NearestCentroidClassifier:
    """Pure Python Nearest-Centroid classifier for zero-dependency transaction scoring."""
    
    def __init__(self):
        self.centroids: Dict[str, List[float]] = {}
        self.bounds: Dict[str, Tuple[float, float]] = {}

    def fit(self, dataset: List[Dict[str, Any]], bounds: Dict[str, Tuple[float, float]]) -> None:
        self.bounds = bounds
        
        # Group features by risk classification status
        grouped: Dict[str, List[List[float]]] = {}
        for entry in dataset:
            status = entry["status"]
            if status not in grouped:
                grouped[status] = []
            grouped[status].append(entry["features"])
            
        # Calculate centroids (mean vector for Safe, Suspicious, High Risk classes)
        for status, features_list in grouped.items():
            num_features = len(features_list[0])
            num_samples = len(features_list)
            
            centroid = [0.0] * num_features
            for features in features_list:
                for i in range(num_features):
                    centroid[i] += features[i]
                    
            centroid = [val / num_samples for val in centroid]
            self.centroids[status] = centroid

    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(v1, v2)))

    def predict(self, normalized_features: List[float]) -> Tuple[str, float]:
        """
        Predicts the class status and returns a raw probability/score 
        inversely proportional to the distance from centroids.
        """
        best_status = "Safe"
        min_distance = float("inf")
        distances = {}
        
        for status, centroid in self.centroids.items():
            dist = self._euclidean_distance(normalized_features, centroid)
            distances[status] = dist
            if dist < min_distance:
                min_distance = dist
                best_status = status
                
        # Compute a raw score from 0.0 to 100.0 based on distance
        # A simple distance-based scaling:
        # Distance to 'Safe' centroid vs 'High Risk' centroid
        safe_dist = distances.get("Safe", 1.0)
        high_risk_dist = distances.get("High Risk", 1.0)
        
        # Avoid division by zero
        total = safe_dist + high_risk_dist
        if total == 0:
            raw_score = 50.0
        else:
            # The closer to High Risk (smaller high_risk_dist), the higher the score
            raw_score = (safe_dist / total) * 100.0
            
        return best_status, raw_score

    def evaluate(self, dataset: List[Dict[str, Any]]) -> float:
        """Evaluates classifier accuracy on the training dataset."""
        correct = 0
        for entry in dataset:
            prediction, _ = self.predict(entry["features"])
            if prediction == entry["status"]:
                correct += 1
        return correct / len(dataset) if dataset else 0.0

    def export_model(self, file_path: str) -> None:
        """Saves model parameters and scaling bounds as JSON."""
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        model_data = {
            "centroids": self.centroids,
            "bounds": self.bounds
        }
        with open(file_path, "w") as f:
            json.dump(model_data, f, indent=2)


if __name__ == "__main__":
    print("Starting Nearest Centroid model training pipeline...")
    dataset, bounds = prepare_dataset()
    
    model = NearestCentroidClassifier()
    model.fit(dataset, bounds)
    
    accuracy = model.evaluate(dataset)
    print("SUCCESS: Model training completed.")
    print(f"Calculated Centroids: {model.centroids}")
    print(f"Training Accuracy: {accuracy * 100:.1f}%")
    
    export_path = "./ml/models/transaction_classifier.json"
    model.export_model(export_path)
    print(f"SUCCESS: Model parameters exported to: {export_path}")
