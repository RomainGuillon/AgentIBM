# 🖥️ Agent Expert IBM AS400

Agent conversationnel expert en administration IBM iSeries (AS400), ERP SIGIP, module OPS et outil ARCAD. Construit avec LangChain + OpenAI, interface Streamlit, observabilité via Langfuse.

## Fonctionnalités

- **IBM OS/400** : commandes CL, gestion des jobs, profils utilisateurs, bibliothèques, sauvegardes, performance, sécurité
- **SIGIP** : menus 5250, procédures fonctionnelles, comptabilité, stocks, commandes, paramétrage
- **OPS** : scheduler, monitoring, alertes, gestion des jobs OPS
- **ARCAD** : cycle de vie applicatif, versioning, promotions entre environnements
- Réponses structurées : **Synthèse → Explication → Commandes**
- Historique conversationnel (10 derniers échanges)
- Observabilité complète via **Langfuse Cloud**

## Prérequis

- Python 3.10+
- Un compte [OpenAI](https://platform.openai.com/) avec une clé API
- *(Optionnel)* Un compte [Langfuse Cloud](https://cloud.langfuse.com/) pour l'observabilité

## Installation locale

```bash
# 1. Cloner le dépôt
git clone https://github.com/<votre-compte>/AgentIBM.git
cd AgentIBM

# 2. Créer et activer l'environnement virtuel
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Configurer les clés API
cp .env.example .env
# Éditer .env et renseigner vos clés

# 5. Lancer l'application
streamlit run app.py
```

## Configuration des clés API

### En local — fichier `.env`

Copier `.env.example` en `.env` et renseigner vos clés :

```env
OPENAI_API_KEY=sk-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_BASE_URL=https://cloud.langfuse.com
```

> ⚠️ Le fichier `.env` est dans `.gitignore` — il ne sera jamais commité sur GitHub.

### Sur Streamlit Cloud

Dans votre app Streamlit Cloud : **Settings → Secrets**, coller :

```toml
OPENAI_API_KEY = "sk-..."
LANGFUSE_PUBLIC_KEY = "pk-lf-..."
LANGFUSE_SECRET_KEY = "sk-lf-..."
LANGFUSE_BASE_URL = "https://cloud.langfuse.com"
```

Les clés sont lues automatiquement au démarrage — aucune saisie manuelle nécessaire dans l'interface.

## Déploiement sur Streamlit Cloud

1. Pousser le dépôt sur GitHub (`.env` et `secrets.toml` sont exclus par `.gitignore`)
2. Connecter le dépôt sur [share.streamlit.io](https://share.streamlit.io)
3. Fichier principal : `app.py`
4. Ajouter les secrets dans **Settings → Secrets**
5. Déployer

## Structure du projet

```
AgentIBM/
├── agent_ibm.py              # Agent LangChain + tools AS400/SIGIP/OPS/ARCAD
├── app.py                    # Interface Streamlit
├── requirements.txt          # Dépendances Python
├── .env                      # Clés API locales (gitignore)
├── .env.example              # Template sans clés (commité)
├── .gitignore
└── .streamlit/
    └── secrets.toml.example  # Template secrets Streamlit Cloud (commité)
```

## Observabilité Langfuse

Quand Langfuse est activé, chaque conversation est tracée avec :
- les appels LLM (modèle, tokens, coût)
- les appels aux tools (commande recherchée, résultat)
- un `session_id` unique par conversation pour regrouper les échanges
- les tags `ibm-expert`, `as400`, `sigip`, `ops`, `arcad`

Vos traces sont visibles sur [cloud.langfuse.com](https://cloud.langfuse.com).

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| LLM | OpenAI GPT-4o |
| Framework agent | LangChain v1.0 + `create_agent` |
| Interface | Streamlit |
| Observabilité | Langfuse Cloud |
| Gestion secrets | `python-dotenv` + `st.secrets` |
