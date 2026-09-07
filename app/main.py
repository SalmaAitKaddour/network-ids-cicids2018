from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, create_model
import numpy as np

from model_loader import load_artifacts

app = FastAPI(
    title="IDS Cloud API",
    description="API de détection d'intrusion (Benign / DDoS / SSH-Bruteforce) basée sur Machine Learning",
    version="1.0.0"
)

# Chargement des artefacts au démarrage de l'API (une seule fois)
model, scaler, label_encoder, feature_names = load_artifacts()

# ============ Construction dynamique du schéma d'entrée ============
# Crée un modèle Pydantic avec un champ float par feature attendue
fields = {name: (float, ...) for name in feature_names}
FlowFeatures = create_model("FlowFeatures", **fields)
"""
c'est equivalent d'ecrire=
class FlowFeatures(BaseModel):
    Protocol: float
    FlowDuration: float
    # ... 33 autres champs"""


"""class FlowFeatures(BaseModel):
    # L'ordre ci-dessous doit rester identique à celui de feature_names.json,
    # car predict() utilise cet ordre pour construire le vecteur d'entrée.
    protocol: float
    flow_duration: float
    fwd_packet_length_max: float
    fwd_packet_length_mean: float
    bwd_packet_length_min: float
    flow_bytes_s: float
    flow_iat_mean: float
    flow_iat_std: float
    flow_iat_max: float
    fwd_iat_std: float
    bwd_iat_total: float
    bwd_iat_mean: float
    bwd_iat_max: float
    bwd_iat_min: float
    fwd_psh_flags: float
    bwd_header_length: float
    fwd_packets_s: float
    bwd_packets_s: float
    packet_length_min: float
    packet_length_mean: float
    packet_length_std: float
    fin_flag_count: float
    psh_flag_count: float
    ack_flag_count: float
    urg_flag_count: float
    ece_flag_count: float
    down_up_ratio: float
    subflow_fwd_bytes: float
    init_fwd_win_bytes: float
    init_bwd_win_bytes: float
    fwd_seg_size_min: float
    active_mean: float
    active_std: float
    active_max: float
    idle_std: float
    idle_min: float"""
class PredictionResponse(BaseModel):
    prediction: str
    prediction_code: int
    probabilities: dict


@app.get("/")
def root():
    return {
        "message": "IDS Cloud API — utilisez POST /predict pour classifier un flux réseau",
        "classes_possibles": list(label_encoder.classes_)
    }


@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}


@app.get("/features")
def get_features():
    """Expose la liste et l'ordre des features attendues, pour que n'importe
    quel frontend (Streamlit, React, script...) puisse construire son
    formulaire sans jamais avoir besoin d'accéder à feature_names.json."""
    return {"feature_names": feature_names, "count": len(feature_names)}


@app.post("/predict", response_model=PredictionResponse)
def predict(flow: FlowFeatures):
    try:
        # Reconstituer le vecteur de features dans le bon ordre
        input_dict = flow.dict()
        X = np.array([[input_dict[name] for name in feature_names]])

        # Appliquer la même normalisation que pendant l'entraînement
        X_scaled = scaler.transform(X)

        # Prédiction
        pred_code = int(model.predict(X_scaled)[0])
        pred_label = label_encoder.inverse_transform([pred_code])[0]

        # Probabilités par classe (si le modèle les supporte)
        proba_dict = {}
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X_scaled)[0]
            proba_dict = {
                cls: round(float(p), 4)
                for cls, p in zip(label_encoder.classes_, proba)
            }

        return PredictionResponse(
            prediction=pred_label,
            prediction_code=pred_code,
            probabilities=proba_dict
        )

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))