# 🔬 Tuteur de Physique-Chimie IA — Collège

Tuteur de physique-chimie pour collégiens (6ᵉ à 3ᵉ), construit sur le modèle de l'app de maths du collège :
**Diagnostic → Entraînement ciblé → Bilan**, en exercices courts, variés et ludiques.

## Fonctionnalités

- 🧭 **Trois façons de choisir le thème** : un chapitre du programme, **📸 la photo d'un exercice fait en classe**, ou un thème libre
- 🃏 **Carte de jeu** : un exercice par écran, points, série, badges et missions selon les centres d'intérêt
- 🔀 **Six formats en rotation** : QCM, réponse numérique (avec unité), vrai ou faux, texte à trous, étapes dans l'ordre (protocoles, raisonnements), réponse rédigée
- 🔌 **Schémas dessinés par l'app** : circuits électriques en série ou en dérivation (pile, lampes, moteur, résistance, DEL, interrupteurs, ampèremètre, voltmètre), graphiques d'expérience, molécules et transformations chimiques en modèles moléculaires
- ✅ **Correction instantanée par l'app** ; les corrigés numériques du tuteur sont recalculés et refusés s'ils sont faux
- 🧪 **Consignes de fond** : unités du collège, valeurs réalistes, conservation des atomes, aucune manipulation dangereuse proposée
- 👩‍🏫 **Espace professeur** (mot de passe) : vue par élève et détail des séances

Vocabulaire du projet : `GLOSSARY.md`. Décisions : `docs/adr/`.

## Architecture

| Fichier | Rôle |
|---|---|
| `app.py` | Page Streamlit : accueil et profil, espace prof, sauvegarde Supabase (table `sessions_physique_college`) |
| `ecran.py` | Écran « carte de jeu » |
| `seance.py` | Déroulé d'une séance (sans Streamlit, testable) |
| `exercices.py` | Contrat d'exercice, correction, rotation des formats, barème |
| `figures.py` | Schémas de physique-chimie (circuits, graphiques, molécules, réactions) |
| `tuteur.py` | Prompts et appels à l'API Claude |
| `progression.py`, `modele.py` | Points et badges cumulés ; exercice modèle photographié |

## Déploiement (Streamlit Cloud + Supabase)

### 1. Base de données

Dans Supabase → **SQL Editor** → coller `supabase_setup.sql` → **Run**.
Le script peut être relancé sans risque. Il fonctionne dans le même projet Supabase que les apps de maths
(table séparée `sessions_physique_college`).

### 2. Application

[share.streamlit.io](https://share.streamlit.io) → *New app* → ce dépôt, branche `main`, fichier `app.py`
→ *Advanced settings* → **Secrets** :

```toml
ANTHROPIC_API_KEY = "sk-ant-..."
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "sb_secret_..."
MOT_DE_PASSE_PROF = "choisissez-un-mot-de-passe"
```

**Utilisez la clé secrète Supabase** (*Project Settings → API Keys*, clé `sb_secret_…`, ou `service_role`
dans *Legacy API Keys*), **jamais la clé publique**. Les élèves sont mineurs : la table n'a aucune politique
d'accès public, et aucun identifiant n'est écrit dans le code. Si la clé manque ou est la clé publique,
l'app fonctionne sans historique et l'espace professeur indique quoi corriger.

## Chapitres

- **6ᵉ** : états de la matière, changements d'état, mélanges, masse et volume, mouvements, énergie, circuits simples, lumière
- **5ᵉ** : changements d'état, solubilité, séparation des mélanges, circuits en série et en dérivation, conducteurs, vitesse, lumière, énergie
- **4ᵉ** : atomes et molécules, combustions, conservation de la masse, masse volumique, intensité et tension, vitesse, couleurs, son
- **3ᵉ** : atome et ions, pH, acide et métal, tests des ions, loi d'Ohm, puissance et énergie, énergies cinétique et potentielle, gravitation, forces, signaux

## Technologies

- **IA** : API Claude (`claude-haiku-4-5`)
- **Schémas** : matplotlib
- **Base de données** : Supabase (PostgreSQL)
- **Interface** : Streamlit

## Tests

```bash
pip install -r requirements.txt pytest
python -m pytest -q tests      # IA et base simulées, aucune clé nécessaire
```
