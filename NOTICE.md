# NOTICE

**Agent Expert IBM AS400** — capitalisation du savoir sur socle IBM iSeries.

**Copyright (c) 2026 Romain Guillon — Tous droits réservés.**

---

## Statut de ce dépôt

Ce dépôt est publié en **accès visible (« source-available »)**, à des fins de
démonstration de compétences. **Ce n'est pas un projet open source.**

Le code peut être lu, installé et exécuté pour évaluer le travail. Il ne peut
être ni copié, ni modifié, ni redistribué, ni utilisé à des fins commerciales.
Les conditions complètes figurent dans le fichier [`LICENSE`](./LICENSE).

Cette restriction couvre explicitement **les prompts système, la définition
des tools et la base de connaissances vérifiée** : c'est là que se trouve le
travail d'ingénierie que ce dépôt sert à démontrer, pas dans le code
d'orchestration.

## Ce que ce projet démontre

Le sujet n'est pas « faire parler un modèle d'AS/400 ». C'est **empêcher un
modèle d'inventer** sur un domaine où l'erreur coûte cher.

Les réponses sont ancrées sur une base vérifiée — commandes CL, domaines ERP,
sujets OPS, contextes de bonnes pratiques — exposée au modèle par des tools
plutôt que laissée à sa mémoire d'entraînement. Une commande qui n'est pas
dans la base n'est pas inventée : elle est signalée comme inconnue.

C'est la différence entre un agent qui impressionne en démonstration et un
agent qu'un exploitant peut utiliser sans vérifier chaque réponse.

## Licence commerciale et prestations

La méthode se transpose à tout socle technique ancien menacé par les départs
en retraite — AS/400, mainframe, ERP maison, automates industriels. Les
prestations associées :

- **Constitution de la base vérifiée** — entretiens avec vos experts, mise en
  forme, validation. C'est l'essentiel du travail, et ce n'est pas
  automatisable.
- **Adaptation des tools et des prompts** à votre vocabulaire, vos procédures
  et vos règles d'exploitation.
- **Déploiement** — installation sur votre infrastructure ou en SaaS,
  authentification, traçabilité des réponses.
- **Transfert de compétences** — vos équipes reprennent la maintenance de la
  base et l'ajout de nouveaux domaines.

**Contact — LinkedIn :** http://www.linkedin.com/in/romain-guillon-data

**GitHub :** https://github.com/RomainGuillon

Vous pouvez aussi ouvrir une
[issue](https://github.com/RomainGuillon/AgentIBM/issues).

## Portée et conditions d'usage

La base de connaissances livrée dans ce dépôt est une **base de
démonstration**, constituée pour illustrer la méthode. Elle ne prétend ni à
l'exhaustivité ni à l'exactitude sur votre installation : les commandes, les
domaines et les procédures d'un site IBM i dépendent de sa configuration, de
sa version et de ses développements spécifiques.

Ne l'utilisez pas comme référence d'exploitation en production sans l'avoir
confrontée à votre propre documentation.

## Secrets et confidentialité

Aucune clé n'est stockée dans ce dépôt. `.env` et `.streamlit/secrets.toml`
sont exclus par `.gitignore` ; `.env.example` ne contient que des
substituts.

Les questions posées à l'agent transitent par l'API OpenAI et, si le tracing
est activé, par Langfuse. Avant tout usage sur des informations internes,
vérifiez que cette architecture est compatible avec votre politique de
confidentialité — un déploiement souverain est possible en prestation.

## Composants tiers

Les dépendances externes restent régies par leurs licences respectives,
listées dans [`requirements.txt`](./requirements.txt) — LangChain, LangGraph,
Streamlit, Langfuse et le SDK OpenAI au premier chef. Les dispositions du
fichier `LICENSE` ne s'appliquent qu'aux éléments originaux créés par
l'auteur.

**IBM**, **AS/400**, **iSeries** et **IBM i** sont des marques d'International
Business Machines Corporation. **ARCAD** est une marque d'ARCAD Software. Ce
projet est une initiative indépendante, sans affiliation, partenariat ni
approbation de ces sociétés.

## Exclusion de l'entraînement de modèles

L'utilisation du contenu de ce dépôt — code, tools, prompts et base de
connaissances — pour l'entraînement, l'affinage ou l'évaluation de modèles
d'apprentissage automatique n'est pas autorisée. Voir l'article 3.g de la
licence.

---

## Antériorité

L'historique Git de ce dépôt, horodaté et signé cryptographiquement, constitue
un élément de preuve de la date de création des travaux qu'il contient.
