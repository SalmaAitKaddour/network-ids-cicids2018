# IDS Cloud API — Détection d'intrusions dans un environnement Cloud par Machine Learning

Mini-projet de fin de module — Cloud Computing
**Master IAC (Intelligence Artificielle et Cybersécurité)** — Faculté Polydisciplinaire de Béni Mellal, Université Sultan Moulay Slimane
Réalisé par **Salma Ait Kaddour** — Année universitaire 2025/2026

---

## 📋 Description du projet

Ce projet met en œuvre une chaîne complète de détection d'intrusions réseau dans un environnement Cloud, basée sur le dataset de référence **CSE-CIC-IDS2018**. Il se décompose en deux grandes parties :

1. **Construction du modèle de Machine Learning** — exploration des données, nettoyage, sélection de variables, encodage/normalisation, entraînement et comparaison de plusieurs algorithmes de classification (détails complets dans le rapport du projet et les notebooks associés).
2. **Déploiement du modèle via une API REST** — le meilleur modèle retenu (**Decision Tree**) est exposé via une **API FastAPI**, qui joue le rôle de backend et peut alimenter plusieurs applications frontend (une interface de démonstration **Streamlit** est fournie à titre d'exemple). L'ensemble est packagé dans une **image Docker** pour un déploiement portable.

Le modèle classe un flux réseau en 3 catégories :
- **Benign** (trafic normal)
- **DDoS attacks-LOIC-HTTP** (déni de service distribué)
- **SSH-Bruteforce** (force brute SSH)

---

## 🏗️ Architecture du projet

```
IDS-API/
├── app/
│   ├── main.py              # API FastAPI (routes, schéma de prédiction)
│   └── model_loader.py      # Chargement du modèle, du scaler, de l'encodeur et des features
├── models/
│   ├── Decision_Tree.pkl    # Modèle entraîné (meilleur compromis performance/légèreté)
│   ├── scaler.pkl           # StandardScaler ajusté sur les données d'entraînement
│   ├── label_encoder.pkl    # Encodeur des labels (Benign / DDoS / SSH-Bruteforce)
│   └── feature_names.json   # Liste ordonnée des 36 features attendues par le modèle
├── streamlit_test_app.py    # Interface cliente de démonstration (frontend)
├── Dockerfile                # Image portable pour déployer l'API
├── requirements.txt          # Dépendances Python
├── .gitignore
└── README.md
```

Le modèle a été sélectionné à l'issue d'une comparaison de 5 algorithmes (Random Forest, Logistic Regression, Decision Tree, SVM, réseau de neurones MLP), le **Decision Tree** offrant le meilleur F1-score (99,94 %) pour un temps d'entraînement nettement plus faible que les alternatives.

---

## 🔌 Backend — API REST (FastAPI)

L'API, nommée **IDS Cloud API**, expose les routes suivantes :

| Méthode | Route | Description |
|---|---|---|
| `GET` | `/` | Message d'accueil + liste des classes possibles |
| `GET` | `/health` | Vérifie que l'API et le modèle sont bien chargés |
| `GET` | `/features` | Retourne la liste ordonnée des 36 features attendues (utile pour construire n'importe quel frontend) |
| `POST` | `/predict` | Envoie un flux réseau (36 features) et reçoit la classe prédite + probabilités |

Une documentation interactive **Swagger** est générée automatiquement par FastAPI, accessible sur `/docs`.

### Exemple de réponse `/predict`
```json
{
  "prediction": "Benign",
  "prediction_code": 0,
  "probabilities": {
    "Benign": 1.0,
    "DDoS attacks-LOIC-HTTP": 0.0,
    "SSH-Bruteforce": 0.0
  }
}
```

---

## 🖥️ Frontend de démonstration (Streamlit)

Une interface Streamlit (`streamlit_test_app.py`) montre comment n'importe quel frontend peut consommer l'API sans jamais accéder directement au modèle : elle récupère dynamiquement la liste des features via `/features`, puis envoie les valeurs à `/predict`. Deux modes de saisie sont proposés : coller un JSON, ou remplir les champs manuellement.

---

## 🐳 Conteneurisation avec Docker

L'API est packagée dans une image Docker (`ids-api:latest`) embarquant le code applicatif (`app/`) et les artefacts du modèle (`models/`), pour un déploiement portable indépendant de l'environnement d'exécution.

---

## ⚙️ Installation et exécution

### Option 1 — En local (sans Docker)

```bash
# 1. Cloner le projet
git clone https://github.com/SalmaAitKaddour/network-ids-cicids2018.git
cd network-ids-cicids2018

# 2. Créer un environnement virtuel (recommandé)
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux / macOS

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Lancer l'API (depuis la racine du projet)
cd app
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

L'API est alors accessible sur **http://localhost:8000**, et la documentation Swagger sur **http://localhost:8000/docs**.

### Option 2 — Avec Docker

```bash
# 1. Construire l'image Docker (depuis la racine du projet, où se trouve le Dockerfile)
docker build -t ids-api:latest .

# 2. Lancer le conteneur
docker run -d -p 8000:8000 --name ids-api-container ids-api:latest

# 3. Vérifier que le conteneur tourne bien
docker ps
```

L'API est accessible sur **http://localhost:8000/docs**, exactement comme en local.

Pour arrêter et supprimer le conteneur :
```bash
docker stop ids-api-container
docker rm ids-api-container
```

### Lancer l'interface Streamlit de démonstration

Dans un second terminal (API déjà lancée, en local ou dans Docker) :

```bash
pip install streamlit requests
streamlit run streamlit_test_app.py
```

Renseigne l'URL de l'API dans la barre latérale :
- `http://localhost:8000` si l'API tourne en local ou dans Docker avec le port mappé
- `http://ids-api:8000` si Streamlit et l'API tournent tous les deux dans des conteneurs sur le même réseau `docker-compose`

---

## 🧪 Tester l'API rapidement

Via `curl` :
```bash
curl -X GET http://localhost:8000/health
curl -X GET http://localhost:8000/features
```

Via Swagger UI : ouvrir `http://localhost:8000/docs`, déplier `POST /predict`, cliquer sur **Try it out**, remplir (ou laisser à 0) les 36 champs, puis **Execute**.

---

## 📊 Résultats du modèle

| Modèle | F1-score (macro) | MCC | Temps d'entraînement |
|---|---|---|---|
| **Decision Tree** ✅ | 99,94 % | 99,86 % | 30,7 s |
| Random Forest | 99,76 % | — | 151,5 s |
| MLP (PyTorch) | 99,66 % | — | — |
| Logistic Regression | ~99 % | 97,96 % | — |
| SVM (LinearSVC) | ~99 % | — | — |

⚠️ Ces performances, bien qu'exceptionnellement élevées, sont cohérentes avec ce qui est documenté dans la littérature scientifique sur ce dataset (forte séparabilité entre les classes de CSE-CIC-IDS2018). Une validation sur un trafic réseau externe resterait nécessaire avant tout déploiement en production réelle.

Détails complets de la méthodologie (nettoyage, diagnostic de fuite de données, comparaison des algorithmes) disponibles dans le rapport du projet.

---

## 📌 Limites et perspectives

- Le déploiement sur une instance **OpenStack** distante n'a pas pu être finalisé (problème de connectivité SSH) ; l'API reste pleinement fonctionnelle en local via Docker.
- Perspectives : finaliser le déploiement OpenStack, intégrer davantage de catégories d'attaques du dataset complet (infiltration, botnet, web attacks), évaluer la robustesse sur un découpage temporel, simuler un flux de trafic en direct.

---

## 📚 Références

- Sharafaldin, I., Lashkari, A. H., & Ghorbani, A. A. (2018). *Toward Generating a New Intrusion Detection Dataset and Intrusion Traffic Characterization*. ICISSP.
- Leevy, J. L., & Khoshgoftaar, T. M. (2020). *A survey and analysis of intrusion detection models based on CSE-CIC-IDS2018 Big Data*. Journal of Big Data, 7(1), 104.
- Documentation FastAPI — https://fastapi.tiangolo.com/
- Documentation Docker — https://docs.docker.com/
- Documentation scikit-learn — https://scikit-learn.org
