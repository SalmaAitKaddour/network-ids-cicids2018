import streamlit as st
import requests
import json

# ------------------------------------------------------------------
# Configuration : URL de l'API (modifiable sans toucher au code)
# ------------------------------------------------------------------
# En local avec l'API lancée hors Docker :        http://localhost:8000
# Si Streamlit ET l'API tournent dans des conteneurs Docker séparés
# sur le même réseau docker-compose, utiliser le nom du service :
#                                                  http://ids-api:8000
API_URL = st.sidebar.text_input("URL de l'API", value="http://localhost:8000")

st.set_page_config(page_title="IDS - Client de l'API", layout="wide")
st.title("IDS — Interface cliente de l'API")
st.write(
    "Cette interface n'exécute plus aucun modèle localement. "
    "Elle envoie les données à l'API FastAPI via HTTP et affiche sa réponse."
)

# ------------------------------------------------------------------
# 1. Vérifier que l'API est joignable (équivalent d'un "ping")
# ------------------------------------------------------------------
def check_api_health():
    try:
        r = requests.get(f"{API_URL}/health", timeout=3)
        r.raise_for_status()
        return True, r.json()
    except requests.exceptions.RequestException as e:
        return False, str(e)


api_ok, health_info = check_api_health()

with st.sidebar:
    st.subheader("État de l'API")
    if api_ok:
        st.success(f"API disponible ✅ — modèle chargé : {health_info.get('model_loaded')}")
    else:
        st.error(f"API injoignable ❌\n\n{health_info}")
        st.caption(
            "Vérifie que le conteneur/l'API tourne bien à l'adresse ci-dessus "
            "(`docker run -p 8000:8000 ids-api` ou `uvicorn main:app`)."
        )

if not api_ok:
    st.stop()  # inutile d'aller plus loin si l'API ne répond pas


# ------------------------------------------------------------------
# 2. Récupérer la liste des features DEPUIS L'API (pas un fichier local)
# ------------------------------------------------------------------
@st.cache_data(ttl=60)  # revalidé toutes les 60s, au cas où le modèle change côté API
def get_feature_names(api_url: str):
    r = requests.get(f"{api_url}/features", timeout=5)
    r.raise_for_status()
    return r.json()["feature_names"]


try:
    feature_names = get_feature_names(API_URL)
except requests.exceptions.RequestException as e:
    st.error(f"Impossible de récupérer la liste des features depuis l'API : {e}")
    st.stop()


# ------------------------------------------------------------------
# 3. Appeler /predict et afficher le résultat (remplace model.predict())
# ------------------------------------------------------------------
def run_prediction(values: dict):
    """Envoie les features à l'API et affiche la réponse — plus aucun
    accès direct au modèle, au scaler ou au label_encoder ici."""
    try:
        response = requests.post(f"{API_URL}/predict", json=values, timeout=5)
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur réseau lors de l'appel à l'API : {e}")
        return

    if response.status_code != 200:
        # L'API a répondu mais avec une erreur (ex: 400, 422, 500)
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        st.error(f"L'API a renvoyé une erreur ({response.status_code}) : {detail}")
        return

    result = response.json()
    st.success(f"Prédiction : {result['prediction']}")
    st.caption(f"Code de classe : {result['prediction_code']}")

    if result.get("probabilities"):
        st.write("Probabilités par classe :")
        for cls, p in result["probabilities"].items():
            st.write(f"- {cls} : {p:.4f}")


tab_paste, tab_manual = st.tabs(["📋 Coller un JSON", "🔢 Saisie manuelle"])

# ------------------------------------------------------------------
# ONGLET 1 : coller directement un dict de valeurs
# ------------------------------------------------------------------
with tab_paste:
    st.write(
        "Colle un objet JSON avec toutes les features en clé et leur valeur, par exemple :"
    )
    example = {name: 0.0 for name in feature_names[:3]}
    example["..."] = "..."
    st.code(json.dumps(example, indent=2), language="json")

    json_text = st.text_area(
        "Colle ton JSON ici",
        height=250,
        placeholder='{\n  "Flow Duration": 1234.5,\n  "Total Fwd Packets": 10,\n  ...\n}',
    )

    if st.button("Prédire depuis le JSON", type="primary"):
        if not json_text.strip():
            st.warning("Colle d'abord un JSON dans le champ ci-dessus.")
        else:
            try:
                pasted_values = json.loads(json_text)
            except json.JSONDecodeError as e:
                st.error(f"JSON invalide : {e}")
                pasted_values = None

            if pasted_values is not None:
                missing = [f for f in feature_names if f not in pasted_values]
                extra = [k for k in pasted_values if k not in feature_names]

                if missing:
                    st.error(f"Features manquantes dans le JSON : {missing}")
                else:
                    if extra:
                        st.info(
                            f"Clés ignorées (absentes des features attendues par l'API) : {extra}"
                        )
                    # On garde uniquement les features attendues, dans le bon ordre
                    clean_values = {name: float(pasted_values[name]) for name in feature_names}
                    run_prediction(clean_values)

# ------------------------------------------------------------------
# ONGLET 2 : saisie manuelle champ par champ
# ------------------------------------------------------------------
with tab_manual:
    st.subheader("Features du flux réseau")

    values = {}
    cols = st.columns(3)
    for i, name in enumerate(feature_names):
        with cols[i % 3]:
            values[name] = st.number_input(name, value=0.0, key=f"manual_{name}")

    if st.button("Prédire", key="predict_manual"):
        run_prediction(values)