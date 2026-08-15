"""
Interface Streamlit — Agent Expert IBM AS400 / SIGIP / OPS / ARCAD
"""

import uuid
import os
import hashlib
import streamlit as st
from dotenv import load_dotenv
from agent_ibm import create_ibm_agent, ask_agent, init_langfuse

# Chargement des clés : .env en local, st.secrets sur Streamlit Cloud
load_dotenv()

def get_secret(key: str) -> str:
    """Lit une clé depuis st.secrets (Streamlit Cloud) ou les variables d'environnement (.env local)."""
    try:
        return st.secrets.get(key, "")
    except Exception:
        return os.getenv(key, "")

# ---------------------------------------------------------------------------
# CONFIG PAGE
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Agent Expert IBM AS400",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# SIDEBAR — Configuration
# ---------------------------------------------------------------------------

with st.sidebar:
    st.title("⚙️ Configuration")
    st.markdown("---")

    st.markdown("### 🤖 OpenAI")

    # Clé lue silencieusement depuis .env ou st.secrets
    api_key = get_secret("OPENAI_API_KEY")

    model = st.selectbox(
        "Modèle",
        options=["gpt-4o", "gpt-4o-mini", "gpt-4-turbo"],
        index=0,
    )

    st.markdown("---")
    st.markdown("### 📊 Langfuse (observabilité)")

    # Clés Langfuse lues silencieusement depuis .env ou st.secrets
    langfuse_pk = get_secret("LANGFUSE_PUBLIC_KEY")
    langfuse_sk = get_secret("LANGFUSE_SECRET_KEY")
    langfuse_available = bool(langfuse_pk and langfuse_sk)

    langfuse_enabled = st.toggle(
        "Activer Langfuse",
        value=langfuse_available,
        disabled=not langfuse_available,
        help="Clés lues depuis .env / st.secrets" if langfuse_available else "Clés LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY manquantes",
    )

    if langfuse_enabled and langfuse_available:
        lf_init_key = f"{langfuse_pk}_{langfuse_sk}"
        if st.session_state.get("langfuse_init_key") != lf_init_key:
            try:
                lf_base_url = get_secret("LANGFUSE_BASE_URL")
                if lf_base_url:
                    os.environ["LANGFUSE_BASE_URL"] = lf_base_url
                init_langfuse(public_key=langfuse_pk, secret_key=langfuse_sk)
                st.session_state.langfuse_init_key = lf_init_key
                st.success("✅ Langfuse connecté")
            except Exception as e:
                st.error(f"❌ Erreur Langfuse : {e}")
                langfuse_enabled = False
    elif langfuse_enabled and not langfuse_available:
        langfuse_enabled = False

    st.markdown("---")
    st.markdown("### 📚 Domaines couverts")
    st.markdown("""
- **AS400 / iSeries** : Commandes CL, jobs, profils, bibliothèques, sauvegardes
- **SIGIP** : Menus, comptabilité, stocks, commandes, paramétrage
- **OPS** : Scheduler, monitoring, alertes, configuration
- **ARCAD** : Cycle de vie applicatif, versioning, promotions
    """)

    st.markdown("---")

    if st.button("🗑️ Effacer la conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.agent = None
        st.session_state.history = []
        st.session_state.session_id = str(uuid.uuid4())
        st.rerun()

    st.markdown("---")
    st.caption("Agent Expert IBM AS400 · LangChain + OpenAI")

# ---------------------------------------------------------------------------
# INITIALISATION DE L'ÉTAT
# ---------------------------------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = []

if "agent" not in st.session_state:
    st.session_state.agent = None

if "history" not in st.session_state:
    st.session_state.history = []

# Identifiant de session unique — regroupe toute la conversation dans Langfuse
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# ---------------------------------------------------------------------------
# EN-TÊTE PRINCIPAL
# ---------------------------------------------------------------------------

st.title("🖥️ Agent Expert IBM AS400")
st.markdown("*Administrateur AS400 · ERP SIGIP · OPS · ARCAD*")

if langfuse_enabled and st.session_state.get("langfuse_init_key"):
    st.caption(f"📊 Langfuse actif · Session : `{st.session_state.session_id[:8]}...`")

st.markdown("---")

# ---------------------------------------------------------------------------
# ZONE DE CHAT
# ---------------------------------------------------------------------------

with st.container():
    if not st.session_state.messages:
        st.info(
            "👋 Bonjour ! Je suis votre agent expert IBM AS400.\n\n"
            "Posez-moi vos questions sur l'administration AS400, l'ERP SIGIP, OPS ou ARCAD. "
            "Je structurerai mes réponses avec une synthèse, une explication et les commandes nécessaires.",
            icon="🖥️",
        )

    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(msg["content"])
        else:
            with st.chat_message("assistant", avatar="🖥️"):
                st.markdown(msg["content"])

# ---------------------------------------------------------------------------
# SAISIE UTILISATEUR
# ---------------------------------------------------------------------------

prompt = st.chat_input("Posez votre question AS400 / SIGIP / OPS / ARCAD...")

if prompt:
    if not api_key:
        st.error("⚠️ Veuillez renseigner votre clé API OpenAI dans la barre latérale.")
        st.stop()

    # Création / recréation de l'agent si nécessaire.
    # On hache la clé API : la valeur en clair ne doit jamais transiter par session_state.
    agent_key = hashlib.sha256(f"{api_key}_{model}".encode()).hexdigest()
    if st.session_state.agent is None or st.session_state.get("agent_key") != agent_key:
        with st.spinner("Initialisation de l'agent..."):
            try:
                st.session_state.agent = create_ibm_agent(api_key=api_key, model=model)
                st.session_state.agent_key = agent_key
            except Exception as e:
                st.error(f"❌ Erreur d'initialisation : {e}")
                st.stop()

    # Affichage du message utilisateur
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Appel à l'agent
    with st.chat_message("assistant", avatar="🖥️"):
        with st.spinner("Analyse en cours..."):
            try:
                response = ask_agent(
                    agent=st.session_state.agent,
                    question=prompt,
                    history=st.session_state.history.copy(),
                    session_id=st.session_state.session_id,
                    langfuse_enabled=langfuse_enabled and bool(st.session_state.get("langfuse_init_key")),
                )

                st.session_state.history.append({"role": "user", "content": prompt})
                st.session_state.history.append({"role": "assistant", "content": response})

                # Limiter l'historique aux 10 derniers échanges (20 messages)
                if len(st.session_state.history) > 20:
                    st.session_state.history = st.session_state.history[-20:]

                st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

            except Exception as e:
                error_msg = f"❌ Erreur lors de l'appel à l'agent : {e}"
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

# ---------------------------------------------------------------------------
# EXEMPLES DE QUESTIONS (affiché seulement au démarrage)
# ---------------------------------------------------------------------------

if not st.session_state.messages:
    st.markdown("### 💡 Exemples de questions")
    col1, col2, col3, col4 = st.columns(4)

    examples = {
        col1: ("**AS400**", [
            "Comment voir les jobs actifs ?",
            "Comment désactiver un profil utilisateur ?",
            "Faire une sauvegarde de bibliothèque",
            "Consulter les logs système",
        ]),
        col2: ("**SIGIP**", [
            "Accéder aux clôtures comptables SIGIP",
            "Sauvegarde des données SIGIP",
            "Gestion des utilisateurs dans SIGIP",
            "Gérer les stocks dans SIGIP",
        ]),
        col3: ("**OPS**", [
            "Démarrer le sous-système OPS",
            "Configurer une alerte CPU dans OPS",
            "Gérer les jobs planifiés OPS",
            "Monitorer l'AS400 avec OPS",
        ]),
        col4: ("**ARCAD**", [
            "Comment promouvoir des objets avec ARCAD ?",
            "Comparer deux versions d'un programme ARCAD",
            "Gérer les dépendances avec ARCAD",
            "Créer un groupe de travail ARCAD",
        ]),
    }

    for col, (titre, questions) in examples.items():
        with col:
            st.markdown(titre)
            for ex in questions:
                if st.button(ex, key=f"ex_{ex}", use_container_width=True):
                    st.session_state._pending_question = ex
                    st.rerun()

# Traitement des questions exemples
if hasattr(st.session_state, "_pending_question") and st.session_state._pending_question:
    pending = st.session_state._pending_question
    st.session_state._pending_question = None
    if api_key and st.session_state.agent:
        st.session_state.messages.append({"role": "user", "content": pending})
        st.session_state.history.append({"role": "user", "content": pending})
        try:
            response = ask_agent(
                agent=st.session_state.agent,
                question=pending,
                history=st.session_state.history[:-1],
                session_id=st.session_state.session_id,
                langfuse_enabled=langfuse_enabled and bool(st.session_state.get("langfuse_init_key")),
            )
            st.session_state.history.append({"role": "assistant", "content": response})
            st.session_state.messages.append({"role": "assistant", "content": response})
        except Exception as e:
            st.session_state.messages.append({"role": "assistant", "content": f"❌ Erreur : {e}"})
        st.rerun()
