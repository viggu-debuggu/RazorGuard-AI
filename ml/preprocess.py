from typing import List, Dict, Any, Tuple

# Mock synthetic transaction telemetry data for training the Centroid Classifier
MOCK_RAW_TRANSACTIONS = [
    # Safe transactions
    {"amount": 1200.0, "location_drift": 2.5, "velocity_1h_including_current": 1, "device_score": 0.1, "status": "Safe"},
    {"amount": 4500.0, "location_drift": 12.0, "velocity_1h_including_current": 2, "device_score": 0.15, "status": "Safe"},
    {"amount": 300.0, "location_drift": 0.5, "velocity_1h_including_current": 1, "device_score": 0.05, "status": "Safe"},
    {"amount": 8000.0, "location_drift": 45.0, "velocity_1h_including_current": 1, "device_score": 0.2, "status": "Safe"},
    
    # Suspicious transactions
    {"amount": 45000.0, "location_drift": 350.0, "velocity_1h_including_current": 4, "device_score": 0.45, "status": "Suspicious"},
    {"amount": 75000.0, "location_drift": 180.0, "velocity_1h_including_current": 3, "device_score": 0.5, "status": "Suspicious"},
    {"amount": 12000.0, "location_drift": 600.0, "velocity_1h_including_current": 5, "device_score": 0.6, "status": "Suspicious"},
    
    # High Risk transactions
    {"amount": 250000.0, "location_drift": 2200.0, "velocity_1h_including_current": 8, "device_score": 0.95, "status": "High Risk"},
    {"amount": 490000.0, "location_drift": 4500.0, "velocity_1h_including_current": 6, "device_score": 0.85, "status": "High Risk"},
    {"amount": 180000.0, "location_drift": 1500.0, "velocity_1h_including_current": 10, "device_score": 0.9, "status": "High Risk"},
]


def clean_outliers(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filters transactions with negative values or extreme anomalies."""
    cleaned = []
    for entry in data:
        if (
            entry["amount"] >= 0
            and entry["location_drift"] >= 0
            and entry["velocity_1h_including_current"] >= 0
            and 0.0 <= entry["device_score"] <= 1.0
        ):
            cleaned.append(entry)
    return cleaned


def get_normalization_bounds(data: List[Dict[str, Any]]) -> Dict[str, Tuple[float, float]]:
    """Calculates min-max boundaries for each numeric feature."""
    amounts = [x["amount"] for x in data]
    drifts = [x["location_drift"] for x in data]
    velocities = [x["velocity_1h_including_current"] for x in data]
    device_scores = [x["device_score"] for x in data]

    return {
        "amount": (float(min(amounts)), float(max(amounts))),
        "location_drift": (float(min(drifts)), float(max(drifts))),
        "velocity_1h_including_current": (float(min(velocities)), float(max(velocities))),
        "device_score": (float(min(device_scores)), float(max(device_scores))),
    }


def normalize_features(
    data: List[Dict[str, Any]], 
    bounds: Dict[str, Tuple[float, float]]
) -> List[Dict[str, Any]]:
    """Applies MinMax scaling to normalize features between 0.0 and 1.0."""
    normalized = []
    for entry in data:
        norm_feat = []
        for key in ["amount", "location_drift", "velocity_1h_including_current", "device_score"]:
            val = entry[key]
            f_min, f_max = bounds[key]
            norm_val = (val - f_min) / (f_max - f_min) if f_max > f_min else 0.0
            norm_feat.append(float(norm_val))

        normalized.append({
            "features": norm_feat,
            "status": entry["status"]
        })
    return normalized


def prepare_dataset() -> Tuple[List[Dict[str, Any]], Dict[str, Tuple[float, float]]]:
    """Cleans and normalizes the mock payment transaction dataset."""
    cleaned = clean_outliers(MOCK_RAW_TRANSACTIONS)
    bounds = get_normalization_bounds(cleaned)
    dataset = normalize_features(cleaned, bounds)
    return dataset, bounds


if __name__ == "__main__":
    dataset, bounds = prepare_dataset()
    print(f"Dataset prepared successfully. Total entries: {len(dataset)}")
    print(f"Feature Bounds: {bounds}")
    print(f"Example normalized record: {dataset[0]}")
