import joblib
import json
import os

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models")

def load_artifacts():
    model = joblib.load(os.path.join(MODELS_DIR, "Decision_Tree.pkl"))
    scaler = joblib.load(os.path.join(MODELS_DIR, "scaler.pkl"))
    label_encoder = joblib.load(os.path.join(MODELS_DIR, "label_encoder.pkl"))

    with open(os.path.join(MODELS_DIR, "feature_names.json"), "r") as f:
        feature_names = json.load(f)

    return model, scaler, label_encoder, feature_names