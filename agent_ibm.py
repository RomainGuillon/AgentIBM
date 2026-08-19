# Copyright (c) 2026 Romain Guillon. Tous droits réservés.
#
# Ce fichier est publié en accès visible à des fins de démonstration.
# Toute reproduction, modification, redistribution ou utilisation
# commerciale est interdite sans autorisation écrite préalable.
# Voir le fichier LICENSE à la racine du dépôt.

"""
Agent Expert IBM AS400 / SIGIP / OPS
Basé sur LangChain v1.0 + create_agent
"""

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool
import os
from langfuse import Langfuse, get_client
from langfuse.langchain import CallbackHandler


# ---------------------------------------------------------------------------
# PROMPT SYSTÈME
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """Tu es un expert IBM iSeries (AS400) et administrateur de l'ERP SIGIP (version ancienne, interface 5250/verte, années 90-2000), du module OPS et de l'outil ARCAD installés sur cette machine.

L'utilisateur peut te poser des questions sur les domaines suivants :
- **IBM OS/400 (iSeries / AS400)** : administration système, commandes CL, jobs, bibliothèques, profils, sauvegardes, performance, sécurité
- **OPS** : scheduler, monitoring, alertes, gestion des jobs OPS
- **ARCAD** : outil de gestion du cycle de vie des applications RPG/COBOL sur AS400 (versioning, comparaison d'objets, promotions entre environnements, gestion des dépendances)
- **SIGIP** : ERP ancienne génération (interface texte 5250), menus, procédures fonctionnelles, paramétrage, comptabilité, stocks, commandes

RÈGLES DE RÉPONSE OBLIGATOIRES — tu dois TOUJOURS structurer ta réponse ainsi :

## 📋 Synthèse
[1 à 3 phrases maximum résumant la demande et l'objectif]

## 💡 Explication
[Contexte technique, pourquoi cette opération est nécessaire, points d'attention importants, précautions à prendre]

## ⚙️ Commandes à exécuter
[Si des commandes sont nécessaires, les lister dans l'ordre avec le format suivant pour chacune :]

**`NOM_COMMANDE`**
→ _Description_ : Ce que fait la commande
→ _Paramètres_ : Les paramètres importants à renseigner
→ _Exemple_ : `NOM_COMMANDE PARAM1(valeur) PARAM2(valeur)`

---
⚠️ **Attention** : [Si applicable, avertissements critiques — sauvegardes, impacts, irréversibilité]

CONTEXTE DE L'ENVIRONNEMENT :
- OS : IBM OS/400 (iSeries / AS400)
- ERP : SIGIP (version ancienne, interface texte 5250, non java)
- Modules installés : OPS (monitoring/scheduler) et ARCAD (gestion du cycle de vie applicatif)
- Les commandes AS400 sont en anglais abrégé IBM standard (ex: WRKACTJOB, SAVLIB, ENDJOB...)
- Les commandes ARCAD sont préfixées (ex: ARCAD_CMPO, ARCAD_PROMO...)
- L'utilisateur est l'administrateur système, il peut exécuter toutes les commandes
- Toujours préciser l'environnement (bibliothèque, profil utilisateur, environnement SIGIP/ARCAD) quand c'est pertinent
- Pour SIGIP : les menus sont accessibles via des options numérotées dans les écrans verts
- Pour OPS : préciser les sous-commandes OPS spécifiques
- Pour ARCAD : préciser l'environnement source/cible et le type d'objet concerné

Si une commande n'est pas applicable (question purement conceptuelle), remplace la section "Commandes" par :
## ℹ️ Informations complémentaires
[Détails additionnels, recommandations, bonnes pratiques]
"""


# ---------------------------------------------------------------------------
# TOOLS AS400 / SIGIP / OPS
# ---------------------------------------------------------------------------

@tool
def get_as400_command_help(commande: str) -> str:
    """Retourne l'aide détaillée sur une commande AS400/iSeries spécifique.

    Args:
        commande: Le nom de la commande AS400 (ex: WRKACTJOB, SAVLIB, ENDJOB)

    Returns:
        Description détaillée de la commande, ses paramètres et son usage
    """
    # Base de commandes AS400 courantes
    commandes_db = {
        "WRKACTJOB": {
            "desc": "Work with Active Jobs — affiche tous les jobs actifs sur le système",
            "params": "SBS(*ALL/*BATCH/*INTER), JOB(*ALL/nom), TYPE(*ALL/*BATCH/*INTER/*AUTOSTART)",
            "usage": "Monitoring temps réel, détection de jobs bloqués, gestion de la charge",
        },
        "ENDJOB": {
            "desc": "End Job — termine un job en cours d'exécution",
            "params": "JOB(numéro/utilisateur/nom), OPTION(*IMMED/*CNTRLD), DELAY(secondes)",
            "usage": "Arrêt contrôlé (*CNTRLD recommandé) ou immédiat (*IMMED en urgence)",
        },
        "SAVLIB": {
            "desc": "Save Library — sauvegarde une bibliothèque complète",
            "params": "LIB(nom_bibliothèque), DEV(tap01/savf), ENDOPT(*LEAVE/*REWIND/*UNLOAD)",
            "usage": "Sauvegarde complète d'une bibliothèque. Nécessite que la bibliothèque soit accessible.",
        },
        "RSTLIB": {
            "desc": "Restore Library — restaure une bibliothèque depuis une sauvegarde",
            "params": "SAVLIB(nom_orig), DEV(tap01/savf), RSTLIB(nom_dest), MBROPT(*ALL/*NEW)",
            "usage": "Restauration complète ou partielle. Attention aux conflits si la biblio existe.",
        },
        "WRKUSRPRF": {
            "desc": "Work with User Profiles — gestion des profils utilisateurs",
            "params": "USRPRF(*ALL/nom_profil)",
            "usage": "Création, modification, suppression et consultation des profils utilisateurs AS400",
        },
        "CHGUSRPRF": {
            "desc": "Change User Profile — modifie un profil utilisateur",
            "params": "USRPRF(nom), STATUS(*ENABLED/*DISABLED), PASSWORD(*SAME/nouveau), PWDEXP(*YES/*NO)",
            "usage": "Activation/désactivation de comptes, changement de mots de passe",
        },
        "STRSBS": {
            "desc": "Start Subsystem — démarre un sous-système",
            "params": "SBS(nom_sous_système)",
            "usage": "Démarrage de QBATCH, QINTER, QCMN ou sous-systèmes personnalisés",
        },
        "ENDSBS": {
            "desc": "End Subsystem — arrête un sous-système",
            "params": "SBS(nom), OPTION(*CNTRLD/*IMMED), DELAY(secondes)",
            "usage": "Arrêt propre d'un sous-système avant maintenance",
        },
        "WRKSPLF": {
            "desc": "Work with Spooled Files — gestion des fichiers spoulés (impressions)",
            "params": "SELECT(*CURRENT/*ALL), USR(nom_user), FORMTYPE(*ALL/type)",
            "usage": "Consultation, impression, suppression des fichiers en attente d'impression",
        },
        "STRDBMON": {
            "desc": "Start Database Monitor — démarre le moniteur de base de données DB2",
            "params": "JOB(*ALL/numéro), OUTFILE(biblio/fichier), COMMENT(texte)",
            "usage": "Analyse des performances SQL, identification des requêtes lentes",
        },
        "WRKJOBSCDE": {
            "desc": "Work with Job Schedule Entries — gestion des jobs planifiés",
            "params": "JOB(*ALL/nom_job)",
            "usage": "Consultation et modification des tâches planifiées (scheduler AS400 natif)",
        },
        "DSPLOG": {
            "desc": "Display Log — affiche le journal système (QHST, QAUDJRN...)",
            "params": "LOG(QHST/QAUDJRN), PERIOD((*AVAIL/*BEGIN/*END)), OUTPUT(*)",
            "usage": "Consultation des logs système, audit de sécurité, diagnostic d'incidents",
        },
        "CHKOBJ": {
            "desc": "Check Object — vérifie l'existence et les droits sur un objet",
            "params": "OBJ(biblio/objet), OBJTYPE(*FILE/*PGM/*LIB/*ALL), AUT(*USE/*CHANGE/*ALL)",
            "usage": "Vérification avant exécution, diagnostic de problèmes d'autorisation",
        },
        "GRTOBJAUT": {
            "desc": "Grant Object Authority — accorde des droits sur un objet",
            "params": "OBJ(biblio/objet), OBJTYPE(*FILE/*PGM/*LIB), USER(profil), AUT(*USE/*CHANGE/*ALL/*EXCLUDE)",
            "usage": "Gestion des droits d'accès AS400 sur fichiers, programmes et bibliothèques",
        },
        "RNMOBJ": {
            "desc": "Rename Object — renomme un objet AS400",
            "params": "OBJ(biblio/ancien_nom), OBJTYPE(*FILE/*PGM/*LIB), NEWOBJ(nouveau_nom)",
            "usage": "Renommage d'objets. Attention aux programmes qui référencent l'ancien nom.",
        },
        "CRTDUPOBJ": {
            "desc": "Create Duplicate Object — duplique un objet AS400",
            "params": "OBJ(biblio/objet), FROMLIB(biblio_source), OBJTYPE(*FILE/*PGM), TOLIB(biblio_dest), NEWOBJ(nouveau_nom)",
            "usage": "Copie d'objets entre bibliothèques, sauvegarde avant modification",
        },
        "WRKMSGQ": {
            "desc": "Work with Message Queue — gestion des files de messages",
            "params": "MSGQ(biblio/file_messages ou *SYSOPR)",
            "usage": "Lecture et gestion des messages système, alertes opérateur, file QSYSOPR",
        },
        "SAVCHGOBJ": {
            "desc": "Save Changed Objects — sauvegarde les objets modifiés depuis une date",
            "params": "LIB(*ALLUSR/biblio), DEV(tap01), REFDATE(date) REFTIME(heure)",
            "usage": "Sauvegarde incrémentale des objets modifiés. Complète SAVLIB pour les sauvegardes différentielles.",
        },
    }

    commande_upper = commande.upper().strip()
    if commande_upper in commandes_db:
        info = commandes_db[commande_upper]
        return (
            f"Commande : {commande_upper}\n"
            f"Description : {info['desc']}\n"
            f"Paramètres principaux : {info['params']}\n"
            f"Usage typique : {info['usage']}"
        )
    return f"Commande '{commande_upper}' non trouvée dans la base locale. Utilise F1 ou HELP sur l'écran AS400 pour l'aide contextuelle, ou consulte IBM Documentation."


@tool
def get_sigip_procedure(domaine: str) -> str:
    """Retourne les procédures et menus SIGIP pour un domaine fonctionnel donné.

    Args:
        domaine: Le domaine SIGIP (ex: comptabilite, stock, commande, parametrage, utilisateurs)

    Returns:
        Les menus, options et procédures SIGIP correspondants
    """
    domaine_lower = domaine.lower().strip()

    sigip_db = {
        "comptabilite": """
SIGIP — Module Comptabilité
Accès : Menu principal → Option 1 (Comptabilité / Finance)
Sous-menus disponibles :
  1.1 — Saisie des écritures comptables (journaux)
  1.2 — Consultation du plan comptable
  1.3 — Lettrage des comptes
  1.4 — Éditions comptables (balance, grand-livre)
  1.5 — Clôture de période / exercice
  1.6 — États financiers (bilan, compte de résultat)
Notes : Les clôtures de période nécessitent l'arrêt des saisies utilisateurs.
""",
        "stock": """
SIGIP — Module Gestion des Stocks
Accès : Menu principal → Option 3 (Stocks / Magasin)
Sous-menus disponibles :
  3.1 — Mouvements de stock (entrées/sorties)
  3.2 — Inventaire (physique, tournant)
  3.3 — Consultation des niveaux de stock
  3.4 — Réapprovisionnement (seuils d'alerte)
  3.5 — Éditions et états stock
  3.6 — Valorisation du stock
Notes : Les inventaires bloquent les mouvements pendant leur durée.
""",
        "commande": """
SIGIP — Module Commandes / Achats
Accès : Menu principal → Option 2 (Achats / Commandes)
Sous-menus disponibles :
  2.1 — Saisie commandes fournisseurs
  2.2 — Suivi des commandes en cours
  2.3 — Réception marchandises
  2.4 — Retours fournisseurs
  2.5 — Éditions commandes
Notes : La réception crée automatiquement les mouvements de stock.
""",
        "parametrage": """
SIGIP — Paramétrage Système
Accès : Menu principal → Option 9 (Administration / Paramétrage)
Sous-menus disponibles :
  9.1 — Paramètres généraux société
  9.2 — Codes journaux comptables
  9.3 — Paramètres TVA et taxes
  9.4 — Exercices comptables (création, clôture)
  9.5 — Numérotation automatique (factures, commandes...)
  9.6 — Codes monnaies et taux de change
ATTENTION : Les modifications de paramétrage sont immédiatement actives et peuvent impacter tous les utilisateurs.
""",
        "utilisateurs": """
SIGIP — Gestion des Utilisateurs et Droits
Accès : Menu principal → Option 9 → Sous-option Utilisateurs
Sous-menus disponibles :
  - Création/modification d'un profil SIGIP
  - Affectation des menus autorisés
  - Droits par module (lecture, saisie, modification, suppression)
  - Consultation des connexions actives
Notes : Les profils SIGIP sont distincts des profils AS400. Un utilisateur a besoin des deux.
""",
        "sauvegarde": """
SIGIP — Sauvegardes des données SIGIP
Les données SIGIP sont stockées dans des bibliothèques AS400 dédiées.
Bibliothèques typiques : SIGIPDAT (données), SIGIPPGM (programmes), SIGIPTMP (temporaires)
Procédure de sauvegarde SIGIP :
  1. Vérifier qu'aucun utilisateur n'est connecté à SIGIP
  2. Depuis AS400 : ENDJOB des jobs SIGIP actifs si nécessaire
  3. Exécuter : SAVLIB LIB(SIGIPDAT) DEV(TAP01) ENDOPT(*REWIND)
  4. Exécuter : SAVLIB LIB(SIGIPPGM) DEV(TAP01) ENDOPT(*LEAVE)
  5. Vérifier le log de sauvegarde dans QHST
""",
    }

    for cle, valeur in sigip_db.items():
        if cle in domaine_lower or domaine_lower in cle:
            return valeur

    return f"Domaine '{domaine}' non trouvé. Domaines disponibles : comptabilite, stock, commande, parametrage, utilisateurs, sauvegarde. Naviguer dans SIGIP : Menu principal → Touche F4 pour la liste complète des options."


@tool
def get_ops_info(sujet: str) -> str:
    """Retourne des informations sur le module OPS installé sur l'AS400.

    Args:
        sujet: Le sujet OPS (ex: scheduler, monitoring, alertes, jobs, configuration)

    Returns:
        Informations et commandes OPS correspondantes
    """
    sujet_lower = sujet.lower().strip()

    ops_db = {
        "scheduler": """
OPS — Planificateur de tâches (Scheduler)
OPS dispose de son propre scheduler qui complète le scheduler natif AS400.
Commandes OPS pour le scheduler :
  OPSWRKJOBSCDE  — Afficher les jobs planifiés OPS
  OPSADDJOBSCDE  — Ajouter une entrée planifiée
  OPSCHGJOBSCDE  — Modifier une entrée planifiée
  OPSDLTJOBSCDE  — Supprimer une entrée planifiée
  OPSHLDSCDE     — Suspendre temporairement une planification
  OPSRLSSCDE     — Reprendre une planification suspendue
Interface OPS : Accès via le menu OPS → Option Scheduler → gestion des jobs planifiés
""",
        "monitoring": """
OPS — Monitoring et Surveillance Système
OPS surveille en temps réel les ressources AS400.
Fonctions de monitoring OPS :
  - Surveillance CPU, mémoire, disque
  - Monitoring des jobs actifs et en attente
  - Surveillance des files de messages (QSYSOPR)
  - Contrôle des sous-systèmes
  - Alertes sur seuils dépassés
Commandes OPS monitoring :
  OPSWRKSYSSTS   — Statut système via OPS
  OPSDSPLOG      — Afficher les logs OPS
  OPSMNTSTT      — Statut du monitoring OPS
""",
        "alertes": """
OPS — Gestion des Alertes
OPS peut envoyer des alertes par message AS400, email ou SNMP.
Configuration des alertes :
  OPSWRKALR      — Afficher les alertes configurées
  OPSADDALR      — Ajouter une règle d'alerte
  OPSCHGALR      — Modifier une alerte existante
  OPSDLTALR      — Supprimer une alerte
Types d'alertes configurables :
  - Seuil CPU > X%
  - Espace disque < X Mo/Go
  - Job en erreur
  - Message spécifique dans QSYSOPR
  - Sous-système arrêté
""",
        "jobs": """
OPS — Gestion des Jobs OPS
OPS exécute ses propres jobs de service sur l'AS400.
Jobs OPS principaux :
  OPSSBS         — Sous-système OPS (doit être actif)
  OPSMON         — Job monitoring principal OPS
  OPSSCH         — Job scheduler OPS
  OPSMSG         — Job gestion des messages OPS
Commandes de gestion :
  STROPSSBS      — Démarrer le sous-système OPS
  ENDOPSSBS      — Arrêter le sous-système OPS
  WRKOPSJOB      — Afficher les jobs OPS actifs
Vérification : WRKACTJOB SBS(OPSSBS) pour voir tous les jobs OPS actifs
""",
        "configuration": """
OPS — Configuration Générale
Accès à la configuration OPS :
  GO OPSMNU      — Menu principal OPS
  WRKCFGOPS      — Configuration générale OPS
Paramètres configurables :
  - Connexions (email, SNMP, notifications)
  - Intervalles de polling monitoring
  - Rétention des logs OPS
  - Profils utilisateurs OPS
  - Licences et activation des modules
Fichiers de configuration : stockés dans la bibliothèque OPSLIB ou OPSDAT selon la version
""",
    }

    for cle, valeur in ops_db.items():
        if cle in sujet_lower or sujet_lower in cle:
            return valeur

    return f"Sujet OPS '{sujet}' non trouvé dans la base. Sujets disponibles : scheduler, monitoring, alertes, jobs, configuration. Utiliser GO OPSMNU sur l'AS400 pour accéder au menu principal OPS."


@tool
def get_best_practices(contexte: str) -> str:
    """Retourne les bonnes pratiques AS400/SIGIP pour un contexte donné.

    Args:
        contexte: Le contexte (ex: sauvegarde, securite, performance, maintenance, migration)

    Returns:
        Les bonnes pratiques recommandées pour ce contexte
    """
    contexte_lower = contexte.lower().strip()

    pratiques_db = {
        "sauvegarde": """
BONNES PRATIQUES — Sauvegardes AS400
✅ Stratégie recommandée :
  1. Sauvegarde complète hebdomadaire (SAVLIB *ALLUSR ou GO SAVE option 21)
  2. Sauvegarde différentielle quotidienne (SAVCHGOBJ)
  3. Sauvegarde des données SIGIP avant toute mise à jour
  4. Tester la restauration régulièrement (RSTLIB sur environnement de test)
✅ Bonnes pratiques :
  - Toujours vérifier le log après sauvegarde (DSPLOG ou consulter QHST)
  - Conserver au moins 3 jeux de sauvegardes (grand-père/père/fils)
  - Documenter les sauvegardes dans un registre
  - Alerter OPS sur l'échec des sauvegardes
⚠️ Pièges courants :
  - Oublier les objets IFS (GO SAVE option 41)
  - Ne pas vérifier l'espace disponible sur la bande/SAVF avant sauvegarde
""",
        "securite": """
BONNES PRATIQUES — Sécurité AS400
✅ Gestion des profils :
  - Désactiver immédiatement les comptes des utilisateurs qui quittent l'entreprise
  - Appliquer le principe du moindre privilège (*USE par défaut)
  - Forcer le changement de mot de passe à la première connexion (PWDEXP *YES)
  - Audit régulier des profils avec WRKUSRPRF *ALL
✅ Journalisation :
  - Activer QAUDJRN pour l'audit de sécurité
  - Monitorer les tentatives de connexion échouées
  - Logger les accès aux objets sensibles
⚠️ À éviter :
  - Utiliser le profil QSECOFR pour les opérations courantes
  - Laisser des profils avec mot de passe *NONE en production
  - Accorder *ALLOBJ sans justification
""",
        "performance": """
BONNES PRATIQUES — Performance AS400
✅ Monitoring régulier :
  - WRKACTJOB : surveiller les jobs à forte consommation CPU
  - WRKSYSSTS : vérifier le taux de pagination (doit rester < 10/s)
  - STRDBMON : analyser les requêtes SQL lentes
✅ Optimisations courantes :
  - Rebuild régulier des index (RGZPFM sur les fichiers très actifs)
  - Nettoyer les fichiers journaux anciens (DLTJRN)
  - Purger les fichiers spoulés anciens (WRKSPLF et suppression)
  - Vérifier et ajuster les pools mémoire si nécessaire
⚠️ Attention SIGIP :
  - Les programmes SIGIP anciens ne sont pas optimisés pour les gros volumes
  - Éviter les éditions volumineuses en heures de pointe
""",
        "maintenance": """
BONNES PRATIQUES — Maintenance AS400
✅ Maintenance planifiée :
  - PTF (Program Temporary Fix) : appliquer régulièrement les correctifs IBM
  - RGZPFM mensuel sur les fichiers SIGIP fragmentés
  - Nettoyage des travaux en attente (WRKJOBQ)
  - Vérification de l'intégrité disque (CHKDSK équivalent AS400 : VRYCFG)
✅ Avant toute maintenance :
  1. Communiquer aux utilisateurs (heure de fin de service)
  2. Sauvegarder avant d'appliquer des modifications
  3. Tester sur un environnement hors-production si possible
  4. Documenter toutes les modifications (journal d'exploitation)
""",
    }

    for cle, valeur in pratiques_db.items():
        if cle in contexte_lower or contexte_lower in cle:
            return valeur

    return f"Contexte '{contexte}' non trouvé. Contextes disponibles : sauvegarde, securite, performance, maintenance, migration."


# ---------------------------------------------------------------------------
# INITIALISATION DE L'AGENT
# ---------------------------------------------------------------------------

def init_langfuse(public_key: str, secret_key: str) -> None:
    """Initialise le client Langfuse singleton.

    Args:
        public_key: Clé publique Langfuse (pk-lf-...)
        secret_key: Clé secrète Langfuse (sk-lf-...)
    """
    host = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
    Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=host,
    )


def create_ibm_agent(api_key: str, model: str = "gpt-4o"):
    """Crée et retourne l'agent Expert IBM.

    Args:
        api_key: Clé API OpenAI
        model: Modèle à utiliser (défaut : gpt-4o)

    Returns:
        L'agent LangChain configuré
    """
    llm = init_chat_model(
        f"openai:{model}",
        temperature=0.2,  # Bas → réponses précises et déterministes
        api_key=api_key,
    )

    tools = [
        get_as400_command_help,
        get_sigip_procedure,
        get_ops_info,
        get_best_practices,
    ]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    return agent


def ask_agent(
    agent,
    question: str,
    history: list = None,
    session_id: str = None,
    langfuse_enabled: bool = False,
) -> str:
    """Interroge l'agent et retourne sa réponse.

    Args:
        agent: L'agent LangChain
        question: La question de l'utilisateur
        history: Historique des messages précédents (liste de dicts)
        session_id: Identifiant de session pour regrouper la conversation dans Langfuse
        langfuse_enabled: Active le tracking Langfuse si True
    """
    messages = history or []
    messages.append({"role": "user", "content": question})

    config = {}
    if langfuse_enabled:
        langfuse_handler = CallbackHandler()
        config = {
            "callbacks": [langfuse_handler],
            "metadata": {
                "langfuse_session_id": session_id or "default",
                "langfuse_tags": ["ibm-expert", "as400", "sigip", "ops", "arcad"],
            },
        }

    result = agent.invoke({"messages": messages}, config=config)

    if langfuse_enabled:
        get_client().flush()

    return result["messages"][-1].content
