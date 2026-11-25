"""Le tuteur (API Claude) : il écrit le contenu, l'app décide du reste (ADR 0001).

Cinq usages, cinq prompts : produire un exercice dans un format imposé, corriger une réponse rédigée,
répondre à une question de l'élève sans donner la solution, rédiger le bilan à partir des chiffres de l'app,
lire la photo d'un exercice modèle (ADR 0002 : jamais résolu, photo jamais conservée).
"""

from __future__ import annotations

import base64
import json
import re

from exercices import NOMS_FORMATS, ExerciceInvalide, valider_exercice
from figures import FigureInvalide
from modele import trop_proche

MODELE = "claude-haiku-4-5-20251001"

SOCLE = """Tu es le tuteur de physique-chimie d'une application pour collégiens (6ᵉ à 3ᵉ).

Règles de fond :
- Rigueur : vérifie chaque énoncé, chaque calcul et chaque corrigé avant de répondre. Un énoncé doit
  contenir toutes les données nécessaires et une seule réponse possible. Les valeurs doivent être
  physiquement réalistes (vitesse du son dans l'air ≈ 340 m/s, de la lumière ≈ 300 000 km/s, eau : 1 kg/L…).
- Niveau : respecte strictement la classe et le programme indiqués ; n'utilise aucune notion d'un niveau supérieur
  (pas de mole, pas de formule de l'énergie cinétique avant la 3ᵉ, etc.).
- Grandeurs et unités : toujours une unité, celles du collège (m, km, s, h, m/s, km/h, g, kg, L, mL, cm³, g/L,
  kg/m³, °C, V, A, Ω, W, J, kWh, N, N/kg). Les conversions sont explicites dans la correction.
- Chimie : écris les formules en Unicode (H₂O, CO₂, O₂, CH₄, Cu²⁺, Cl⁻) ; une transformation chimique conserve
  les atomes. Démarche scientifique : observation, hypothèse, expérience, conclusion.
- Sécurité : ne propose JAMAIS une manipulation dangereuse à faire seul ou à la maison (acides, flamme, électricité
  du secteur) ; rappelle les règles du labo (lunettes, blouse) quand c'est pertinent.
- Ton : bienveillant, encourageant, vocabulaire accessible, sans infantiliser. Valorise une démarche précise
  plutôt qu'un compliment générique.
- Écriture : PAS de LaTeX. Unicode lisible : ², ³, ×, ÷, ≈, ≤, ≥, →, Ω. Ex. « v = d ÷ t », « P = U × I ».
- Français, phrases courtes."""

SPECIFICATIONS = {
    "qcm": """"options": 4 propositions courtes (dont des erreurs typiques d'élèves, plausibles),
"bonne_option": le texte EXACT de la bonne proposition.""",
    "numerique": """"calcul": l'expression qui donne la réponse exacte, avec seulement des nombres (déjà convertis dans les bonnes
  unités), + - * / **, sqrt() et pi (ex. "1200/(2.5*60)" pour v = d ÷ t) ; l'app la recalcule pour vérifier ton corrigé,
"reponse": la valeur attendue, déjà arrondie comme demandé (nombre, pas texte),
"arrondi": "unité", "dixième", "centième" ou "exact",
"unite": l'unité de la réponse, obligatoire en physique-chimie ("m/s", "km/h", "A", "V", "Ω", "g/L", "kg/m³", "J"…).""",
    "vf": """"affirmations": 3 affirmations [{"texte": "...", "vrai": true/false}], qui testent la compréhension
  (pas seulement la mémoire) ; au moins une vraie et une fausse.""",
    "trous": """"texte": une phrase ou une formule où chaque trou est marqué exactement par ___ (trois tirets bas),
"trous": dans l'ordre, pour chaque ___ : {"options": 3 propositions courtes, "bonne": la bonne, texte exact}.""",
    "ordre": """"etapes": 4 étapes d'un raisonnement ou d'un calcul, DANS LE BON ORDRE, chacune une phrase courte
  et autonome (l'app les mélange ; un ordre doit être le seul logique).""",
    "ouvert": """"attendus": les éléments qu'une bonne réponse rédigée doit contenir (caché à l'élève, sert à corriger).
L'énoncé demande une justification courte (1 à 3 phrases) : « Explique pourquoi… », « Justifie… ».""",
}

FIGURES = """"figure": null, OU un schéma si il aide vraiment. L'app le dessine (symboles normalisés). Types :
  Circuit en série : {"type": "circuit", "montage": "serie", "composants": [...]}   (2 à 6 composants, dans l'ordre)
  Circuit en dérivation : {"type": "circuit", "montage": "derivation", "composants": [la pile et 0 à 2 composants
      de la branche principale], "branches": [[...], [...]]}   (2 ou 3 branches de 1 ou 2 composants)
    Composants : "pile" (exactement une), "lampe", "moteur", "resistance", "del", "interrupteur_ferme",
    "interrupteur_ouvert", "amperemetre" ; ou un objet {"type": "lampe", "nom": "L1", "valeur": "6 V",
    "voltmetre": true} (voltmetre: true branche un voltmètre aux bornes de ce composant ; au plus deux).
  Graphique d'expérience : {"type": "graphique", "titre": "...", "x": {"nom": "Temps", "unite": "min"},
      "y": {"nom": "Température", "unite": "°C"}, "points": [[0, -10], [2, 0], ...], "style": "courbe" ou "points"}
      (2 à 40 points ; pour une courbe, les x sont croissants)
  Molécule ou ion : {"type": "molecule", "formule": "H2O"}
  Transformation chimique (modèles moléculaires) : {"type": "reaction", "reactifs": [{"formule": "CH4", "nombre": 1},
      {"formule": "O2", "nombre": 2}], "produits": [{"formule": "CO2", "nombre": 1}, {"formule": "H2O", "nombre": 2}]}
    Formules disponibles : H2, O2, N2, Cl2, H2O, CO2, CO, CH4, NH3, HCl, SO2, C, O, H, S, Fe, Cu, Zn, Na,
    H+, Na+, Cl-, Cu2+, Fe2+, Fe3+, Zn2+, OH-.
  Les valeurs du schéma doivent être exactement celles de l'énoncé. Ne mets jamais sur le schéma la réponse
  que l'élève doit trouver (une valeur à calculer n'apparaît pas)."""

NIVEAUX = {
    "facile": "application directe en une étape, nombres simples",
    "moyen": "deux étapes, ou une petite mise en situation",
    "difficile": "plusieurs étapes, une réciproque ou un petit problème à décoder",
}

PROMPT_EXERCICE = SOCLE + """

Ta tâche : écrire UN exercice, dans le format imposé par l'application. Tu n'écris rien d'autre.

Réponds UNIQUEMENT avec un objet JSON :
{{
 "format": "{format}",
 "notion": "la notion travaillée en 2 à 5 mots (ex. « loi d'additivité des tensions »)",
 "mission": "une phrase de mise en situation concrète et vivante (vie quotidienne, sport, cuisine…), différente des précédentes",
 "enonce": "la consigne, claire et complète, sans la solution",
 {specification}
 {figures},
 "indices": ["indice 1 : une piste qui oriente sans donner la méthode", "indice 2 : plus explicite, donne la méthode sans le résultat"],
 "correction": "la correction complète et rédigée, étape par étape"
}}
"""

PROMPT_REDACTION = SOCLE + """

Ta tâche : corriger la réponse rédigée d'un élève à un exercice. Sois juste et précis : une réponse correcte
formulée avec ses mots est juste ; une réponse sans justification alors qu'on en demande une est partielle.
Ne redonne pas toute la correction : dis ce qui est juste, ce qui manque ou est faux, en 2 phrases maximum.

Réponds UNIQUEMENT avec un objet JSON :
{"verdict": "juste" | "partiel" | "faux", "retour": "2 phrases maximum, adressées à l'élève (tu)"}
"""

PROMPT_QUESTION = SOCLE + """

L'élève fait un exercice et te pose une question. Réponds en 80 mots maximum, en t'adressant à lui (tu).
{consigne}
Si sa question n'a rien à voir avec la physique-chimie ou l'exercice, ramène-le gentiment à l'exercice."""

PROMPT_BILAN = SOCLE + """

Ta tâche : rédiger le bilan de fin de séance pour l'élève, en 5 lignes maximum, en t'adressant à lui (tu) :
- notion travaillée ;
- acquis observés ;
- point à consolider ;
- degré d'autonomie ;
- prochaine étape recommandée.
Appuie-toi UNIQUEMENT sur les chiffres et résultats fournis par l'application, qui sont exacts.
Ne conclus pas à une maîtrise durable à partir d'une seule séance. Termine sur une note encourageante et précise."""


PROMPT_LECTURE = """Tu lis la photo d'un exercice de physique-chimie qu'un collégien a fait en classe. L'application
s'en servira pour lui créer des exercices DU MÊME TYPE. Tu ne fais que recopier l'énoncé.

Règles :
- Recopie fidèlement l'énoncé (consigne, données, questions), en texte simple, sans LaTeX (π, ², √, ×…).
- Si un schéma accompagne l'exercice, décris-le en une phrase avec ses valeurs (« Schéma : pile, interrupteur fermé et deux lampes L1 et L2 en série »).
- NE RÉSOUS PAS l'exercice. Ne recopie aucune réponse, aucun calcul, aucune correction écrits par l'élève ou le professeur.
- Ne recopie aucun nom de personne réelle, d'établissement ou de professeur : remplace-les par « l'élève », « le collège ».
- S'il y a plusieurs exercices, recopie seulement le premier qui est entièrement visible.
- Si la photo est floue, coupée, ou ne montre pas un exercice de physique-chimie (ou de sciences), dis-le.

Réponds UNIQUEMENT avec un objet JSON :
{"lisible": true ou false, "matiere": true ou false, "transcription": "l'énoncé recopié", "notion": "la notion travaillée en 2 à 5 mots"}"""

CONSIGNE_MODELE = (
    "L'élève s'entraîne à partir d'un exercice fait en classe (exercice modèle). Crée une VARIANTE du même type : "
    "même méthode et mêmes notions, mais d'autres nombres et une autre situation. Ne recopie jamais l'exercice "
    "modèle et ne donne jamais sa solution : l'élève doit pouvoir le refaire seul ensuite."
)


class TuteurIndisponible(RuntimeError):
    pass


def _client(cle_api: str):
    from anthropic import Anthropic

    return Anthropic(api_key=cle_api)


def _appeler(cle_api: str, systeme: str, messages: list[dict], max_tokens: int = 1500) -> str:
    try:
        reponse = _client(cle_api).messages.create(model=MODELE, system=systeme, messages=messages, max_tokens=max_tokens)
    except Exception as ex:  # réseau, quota, clé…
        raise TuteurIndisponible(str(ex)[:200]) from ex
    return "".join(getattr(b, "text", "") for b in reponse.content).strip()


def extraire_json(texte: str):
    bloc = re.search(r"```(?:json)?\s*(.*?)```", texte, re.S)
    if bloc:
        texte = bloc.group(1)
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin <= debut:
        raise ValueError("Aucun objet JSON dans la réponse")
    return json.loads(texte[debut : fin + 1])


PROMPT_CARTES = SOCLE + """

Ta tâche : écrire des flashcards de révision (une question au recto, la réponse au verso) sur le chapitre indiqué,
pour la classe indiquée. L'élève les retourne et s'évalue lui-même : la réponse doit donc être sûre et sans ambiguïté.

Règles :
- Une seule notion par carte. Recto : une question courte et précise (pas de « Parle-moi de… »).
- Verso : la réponse en 1 ou 2 phrases au plus, avec l'unité quand c'est une grandeur (« ρ = m ÷ V, en g/mL »).
- Varie les types : définition, formule et unités, ordre de grandeur, loi, protocole ou test chimique, schéma à reconnaître.
- Pas deux cartes sur la même question. Respecte le niveau de la classe.
- "figure" : null, ou un schéma qui sert la question (ex. un circuit pour « Ce montage est-il en série ? »,
  une molécule pour « Quelle est cette molécule ? »). La réponse ne doit pas être écrite sur le schéma.
{figures}

Réponds UNIQUEMENT avec un objet JSON :
{{"cartes": [{{"recto": "...", "verso": "...", "figure": null}}, ...]}}"""


def generer_cartes(cle_api: str, profil: dict, nombre: int, deja: list[str] | None = None) -> list[dict]:
    """Flashcards validées pour le chapitre du profil ; réessaie une fois si la réponse est inutilisable."""
    from flashcards import CartesInvalides, valider_cartes

    demande = (f"Classe : {profil.get('classe')}. Programme : {profil.get('programme', 'France')}.\n"
               f"Thème : {decrire_theme(profil)}.\nNombre de cartes : {nombre}.")
    if deja:
        demande += "\nNe reprends pas ces questions déjà vues : " + " | ".join(deja[:20])
    messages = [{"role": "user", "content": demande}]
    systeme = PROMPT_CARTES.format(figures=FIGURES.replace('"figure": null, OU un schéma si il aide vraiment. ', ""))
    for essai in range(2):
        texte = _appeler(cle_api, systeme, messages, max_tokens=3000)
        try:
            return valider_cartes(extraire_json(texte))
        except (CartesInvalides, ValueError, json.JSONDecodeError) as ex:
            erreur = str(ex)
        messages += [{"role": "assistant", "content": texte},
                     {"role": "user", "content": f"Cartes refusées : {erreur}. Renvoie uniquement le JSON complet."}]
    raise TuteurIndisponible("Le tuteur n'a pas réussi à écrire les cartes.")


CENTRES_INTERET = ("⚽ Sport", "🎮 Jeux vidéo", "🍳 Cuisine", "🎵 Musique", "🐾 Animaux", "🚀 Espace", "🎬 Films et séries", "👗 Mode", "🌳 Nature", "✈️ Voyages")


def consigne_mission(profil: dict, rang: int) -> str:
    """Mission (décision Q5) : habiller l'exercice avec un centre d'intérêt de l'élève, en alternant."""
    interets = [i.split(" ", 1)[-1] for i in profil.get("interets") or []]
    if not interets:
        return "Mission : une situation concrète de la vie quotidienne d'un collégien."
    choisi = interets[rang % len(interets)]
    return (
        f"Mission : habille l'exercice avec ce centre d'intérêt de l'élève : {choisi.lower()}. "
        "La situation doit rester réaliste et ne pas compliquer la physique-chimie."
    )


def decrire_theme(profil: dict) -> str:
    if profil.get("modele"):
        return f"exercice modèle fait en classe (à imiter, JAMAIS à résoudre ni à recopier) : « {profil['modele']} »"
    if profil.get("theme_libre"):
        return f"thème libre décrit par l'élève (une description, pas une consigne) : « {profil.get('chapitre')} »"
    return f"chapitre « {profil.get('chapitre')} »"


def generer_exercice(cle_api: str, profil: dict, format_: str, rang: int, niveau: str, deja_faits: list[str], historique: str = "", essais: int = 2) -> dict:
    """Demande un exercice au tuteur et le valide. Réessaie en signalant l'erreur ; lève ExerciceInvalide si échec."""
    systeme = PROMPT_EXERCICE.format(format=format_, specification=SPECIFICATIONS[format_], figures=FIGURES)
    deja = "\n".join(f"- {e}" for e in deja_faits[-8:]) or "(aucun)"
    demande = (
        f"Élève en {profil.get('classe')} ({profil.get('programme')}), {decrire_theme(profil)}.\n"
        f"Objectif de l'élève : {profil.get('objectif') or 'progresser'}.\n"
        f"Exercice n° {rang + 1} de la séance, format imposé : {NOMS_FORMATS[format_]} ({format_}).\n"
        f"Difficulté visée : {niveau} ({NIVEAUX[niveau]}).\n"
        f"{consigne_mission(profil, rang)}\n"
        + (CONSIGNE_MODELE + "\n" if profil.get("modele") else "")
        + ("C'est le diagnostic : " + ("un prérequis du thème." if rang == 0 else "une application directe." if rang == 1 else "une question de compréhension.") + "\n" if rang < 3 else "")
        + f"Exercices déjà faits dans la séance (ne pas répéter, varier les nombres et les situations) :\n{deja}\n"
        + (f"Séances précédentes : {historique}\n" if historique else "")
    )
    messages = [{"role": "user", "content": demande}]
    derniere_erreur = ""
    for _ in range(essais):
        texte = _appeler(cle_api, systeme, messages)
        try:
            ex = valider_exercice(extraire_json(texte), format_)
            copie = trop_proche(ex, profil["modele"]) if profil.get("modele") else None
            if copie:
                raise ExerciceInvalide(copie)
            return ex
        except (ExerciceInvalide, FigureInvalide, ValueError, json.JSONDecodeError) as ex:
            derniere_erreur = str(ex)
        except Exception as ex:  # réponse de forme imprévue : on la traite comme un exercice invalide, jamais un plantage
            derniere_erreur = f"réponse mal formée ({type(ex).__name__})"
        messages += [
            {"role": "assistant", "content": texte},
            {"role": "user", "content": f"Exercice refusé par l'application : {derniere_erreur}. Corrige et renvoie uniquement le JSON complet."},
        ]
    raise ExerciceInvalide(derniere_erreur or "exercice invalide")


def corriger_redaction(cle_api: str, profil: dict, ex: dict, reponse: str) -> dict:
    contenu = (
        f"Classe : {profil.get('classe')}.\nÉnoncé : {ex['mission']} {ex['enonce']}\n"
        f"Éléments attendus (correcteur) : {ex['attendus']}\nCorrection de référence : {ex['correction']}\n"
        f"Réponse de l'élève : « {reponse[:1500]} »"
    )
    texte = _appeler(cle_api, PROMPT_REDACTION, [{"role": "user", "content": contenu}], max_tokens=400)
    try:
        r = extraire_json(texte)
    except (ValueError, json.JSONDecodeError):
        return {"verdict": "partiel", "retour": "Je n'ai pas réussi à analyser ta réponse : compare-la avec la correction."}
    verdict = r.get("verdict") if r.get("verdict") in ("juste", "partiel", "faux") else "partiel"
    return {"verdict": verdict, "retour": str(r.get("retour", ""))[:500]}


def repondre_question(cle_api: str, profil: dict, ex: dict, question: str, correction_vue: bool, echanges: list[dict]) -> str:
    if correction_vue:
        consigne = "L'élève a déjà vu la correction : tu peux l'expliquer en détail."
    else:
        consigne = (
            "Ne donne PAS la réponse ni le résultat final de l'exercice, même s'il le demande : aide-le à avancer "
            "(rappel de cours, question qui le guide, vérification de sa démarche). S'il veut la solution, dis-lui "
            "d'utiliser le bouton « Voir la correction »."
        )
    if profil.get("modele"):
        consigne += (
            "\nL'élève s'entraîne à partir d'un exercice fait en classe (exercice modèle, ci-dessous). Ne résous JAMAIS "
            "cet exercice modèle et n'en donne pas le résultat, même s'il insiste : ramène-le à la variante en cours, "
            "dont la méthode lui permettra de refaire son exercice de classe seul."
        )
    contexte = (
        f"Classe : {profil.get('classe')}. Exercice ({NOMS_FORMATS[ex['format']]}) : {ex['mission']} {ex['enonce']}\n"
        f"Correction (pour toi seul) : {ex['correction']}"
        + (f"\nExercice modèle de l'élève (à ne jamais résoudre) : {profil['modele']}" if profil.get("modele") else "")
    )
    messages = [{"role": "user", "content": contexte}, {"role": "assistant", "content": "D'accord, j'aide l'élève sur cet exercice."}]
    for e in echanges[-6:]:
        messages += [{"role": "user", "content": e["question"]}, {"role": "assistant", "content": e["reponse"]}]
    messages.append({"role": "user", "content": question[:800]})
    return _appeler(cle_api, PROMPT_QUESTION.format(consigne=consigne), messages, max_tokens=400)


def rediger_bilan(cle_api: str, profil: dict, stats: dict, resultats: list[dict]) -> str:
    detail = "\n".join(
        f"- {r['phase']} · {NOMS_FORMATS[r['format']]} · {r.get('notion') or '?'} : "
        + ("réussi" if r["reussi"] else "non réussi")
        + (f", {r['indices']} indice(s)" if r.get("indices") else "")
        + (", correction vue" if r.get("correction_vue") else "")
        + (f", {r['essais']} essais" if r.get("essais", 1) > 1 else "")
        for r in resultats
    )
    contenu = (
        f"Élève : {profil.get('nom')}, {profil.get('classe')}, {decrire_theme(profil)}.\n"
        f"Chiffres de la séance (calculés par l'application) : {json.dumps(stats, ensure_ascii=False)}\n"
        f"Détail des exercices :\n{detail}"
    )
    return _appeler(cle_api, PROMPT_BILAN, [{"role": "user", "content": contenu}], max_tokens=500)


def lire_exercice(cle_api: str, image_jpeg: bytes) -> dict:
    """Transcription d'un exercice modèle photographié. La photo n'est ni conservée ni renvoyée."""
    image = {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": base64.standard_b64encode(image_jpeg).decode()}}
    texte = _appeler(cle_api, PROMPT_LECTURE, [{"role": "user", "content": [image, {"type": "text", "text": "Lis cet exercice."}]}], max_tokens=1200)
    try:
        r = extraire_json(texte)
    except (ValueError, json.JSONDecodeError):
        return {"lisible": False, "matiere": False, "transcription": "", "notion": ""}
    transcription = str(r.get("transcription") or "").strip()[:1500]
    return {
        "lisible": bool(r.get("lisible")) and bool(transcription),
        "matiere": bool(r.get("matiere")),
        "transcription": transcription,
        "notion": str(r.get("notion") or "").strip()[:60],
    }
