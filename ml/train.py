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
    import random
    print("Starting Nearest Centroid model training pipeline...")
    dataset, bounds = prepare_dataset()
    
    # Set seed for reproducible splitting
    random.seed(42)
    shuffled = list(dataset)
    random.shuffle(shuffled)
    
    # 75/25 Train/Test split
    split_idx = int(len(shuffled) * 0.75)
    train_data = shuffled[:split_idx]
    test_data = shuffled[split_idx:]
    
    print(f"Total entries: {len(shuffled)} | Train size: {len(train_data)} | Test size: {len(test_data)}")
    
    # Train model on training split
    model = NearestCentroidClassifier()
    model.fit(train_data, bounds)
    
    # Evaluate on training split
    train_accuracy = model.evaluate(train_data)
    
    # Evaluate on test split
    y_true = [entry["status"] for entry in test_data]
    y_pred = []
    for entry in test_data:
        pred_status, _ = model.predict(entry["features"])
        y_pred.append(pred_status)
        
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    test_accuracy = correct / len(test_data) if test_data else 0.0
    
    # Compute Precision, Recall, F1 for each class
    classes = ["Safe", "Suspicious", "High Risk"]
    metrics = {}
    for cls in classes:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p == cls)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != cls and p == cls)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == cls and p != cls)
        
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        support = sum(1 for t in y_true if t == cls)
        
        metrics[cls] = {"precision": prec, "recall": rec, "f1": f1, "support": support}
        
    print("\nSUCCESS: Model training completed.")
    print(f"Calculated Centroids: {model.centroids}")
    print(f"Training Accuracy: {train_accuracy * 100:.1f}%")
    print(f"Test Accuracy:     {test_accuracy * 100:.1f}%\n")
    
    print("---------------------------------------------------------------")
    print(f"{'Class':<12} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}")
    print("---------------------------------------------------------------")
    for cls in classes:
        m = metrics[cls]
        print(f"{cls:<12} | {m['precision']:<10.3f} | {m['recall']:<10.3f} | {m['f1']:<10.3f} | {m['support']:<8}")
    print("---------------------------------------------------------------")
    
    export_path = "./ml/models/transaction_classifier.json"
    model.export_model(export_path)
    print(f"\nSUCCESS: Model parameters exported to: {export_path}")

