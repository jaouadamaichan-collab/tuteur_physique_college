"""Exercices valides de physique-chimie, un par format, tels que le tuteur doit les renvoyer (JSON brut)."""

import copy

BANQUE = {
    "qcm": {
        "format": "qcm", "notion": "masse volumique", "mission": "Lina prépare un cocktail de jus de fruits en couches.",
        "enonce": "Quelle relation donne la masse volumique ρ d'un liquide de masse m et de volume V ?",
        "options": ["ρ = m ÷ V", "ρ = m × V", "ρ = V ÷ m", "ρ = m + V"], "bonne_option": "ρ = m ÷ V",
        "figure": None, "indices": ["C'est une masse par unité de volume.", "Unité : g/mL, donc une masse divisée par un volume."],
        "correction": "ρ = m ÷ V, en g/mL ou kg/m³.",
    },
    "numerique": {
        "format": "numerique", "notion": "vitesse moyenne", "mission": "Lina court un 400 m en 75 s.",
        "enonce": "Calcule sa vitesse moyenne en m/s.", "calcul": "400/75", "reponse": 5.3, "arrondi": "dixième", "unite": "m/s",
        "figure": {"type": "graphique", "titre": "Course de Lina", "x": {"nom": "Temps", "unite": "s"},
                   "y": {"nom": "Distance", "unite": "m"}, "points": [[0, 0], [25, 140], [50, 270], [75, 400]]},
        "indices": ["Utilise v = d ÷ t.", "v = 400 ÷ 75."], "correction": "v = 400 ÷ 75 ≈ 5,3 m/s.",
    },
    "vf": {
        "format": "vf", "notion": "circuit en série", "mission": "Lina répare la guirlande de son sapin.", "enonce": "Vrai ou faux ?",
        "affirmations": [
            {"texte": "Dans un circuit en série, si une lampe grille, l'autre s'éteint.", "vrai": True},
            {"texte": "Dans un circuit en série, l'intensité change d'un point à l'autre.", "vrai": False},
            {"texte": "Un interrupteur ouvert empêche le courant de circuler.", "vrai": True},
        ],
        "figure": {"type": "circuit", "montage": "serie", "composants": ["pile", "interrupteur_ferme", "lampe", "lampe"]},
        "indices": ["Dans un circuit en série, il n'y a qu'une seule boucle.", "Loi d'unicité de l'intensité."],
        "correction": "Vrai, faux (même intensité partout), vrai.",
    },
    "trous": {
        "format": "trous", "notion": "transformation chimique", "mission": "Lina regarde la flamme de la gazinière.",
        "enonce": "Complète.",
        "texte": "Lors de la combustion du méthane, les atomes se ___ : leur nombre total est ___.",
        "trous": [{"options": ["réarrangent", "détruisent", "multiplient"], "bonne": "réarrangent"},
                  {"options": ["conservé", "doublé", "divisé par deux"], "bonne": "conservé"}],
        "figure": {"type": "reaction", "reactifs": [{"formule": "CH4", "nombre": 1}, {"formule": "O2", "nombre": 2}],
                   "produits": [{"formule": "CO2", "nombre": 1}, {"formule": "H2O", "nombre": 2}]},
        "indices": ["Compte les atomes de chaque côté.", "Rien ne se perd, rien ne se crée."],
        "correction": "Les atomes se réarrangent ; leur nombre est conservé.",
    },
    "ordre": {
        "format": "ordre", "notion": "loi d'Ohm", "mission": "Lina mesure une résistance au labo.", "enonce": "Remets dans l'ordre.",
        "etapes": ["On mesure U = 6 V aux bornes de la résistance.", "On mesure I = 0,02 A dans le circuit.",
                   "On applique la loi d'Ohm : R = U ÷ I.", "R = 6 ÷ 0,02 = 300 Ω."],
        "figure": {"type": "circuit", "montage": "serie", "composants": ["pile", {"type": "resistance", "voltmetre": True}, "amperemetre"]},
        "indices": ["On mesure d'abord.", "Puis on calcule."], "correction": "Mesures, loi, calcul.",
    },
    "ouvert": {
        "format": "ouvert", "notion": "masse volumique et flottaison", "mission": "Un glaçon dans un verre d'eau.",
        "enonce": "Explique pourquoi le glaçon flotte.", "attendus": "Masse volumique de la glace (0,92 g/mL) plus petite que celle de l'eau (1 g/mL).",
        "figure": None, "indices": ["Compare les masses volumiques.", "Un corps moins dense que l'eau flotte."],
        "correction": "La glace est moins dense que l'eau liquide : elle flotte.",
    },
}


def exercice(format_):
    return copy.deepcopy(BANQUE[format_])


def bonne_reponse(ex):
    """Bonne réponse d'un exercice validé (format fermé)."""
    f = ex["format"]
    return {
        "qcm": lambda: ex["bonne_option"],
        "numerique": lambda: "5,3",
        "vf": lambda: [a["vrai"] for a in ex["affirmations"]],
        "trous": lambda: [t["bonne"] for t in ex["trous"]],
        "ordre": lambda: list(ex["etapes"]),
    }[f]()
