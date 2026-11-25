"""Schémas de physique-chimie : vérifiés puis dessinés par l'app (circuits, graphiques, molécules, réactions)."""

import pytest

import tuteur as T
from figures import FORMULES, TYPES, FigureInvalide, atomes_de, dessiner, nom_affiche, valider_figure

PNG = b"\x89PNG\r\n\x1a\n"

VALIDES = [
    {"type": "circuit", "montage": "serie", "composants": ["pile", "interrupteur_ferme", {"type": "lampe", "voltmetre": True}, "moteur", "amperemetre"]},
    {"type": "circuit", "montage": "serie", "composants": ["pile", "interrupteur_ouvert", "del", {"type": "resistance", "valeur": "220 Ω"}]},
    {"type": "circuit", "montage": "derivation", "composants": ["pile", "interrupteur_ferme"],
     "branches": [["lampe"], [{"type": "resistance", "valeur": "100 Ω"}, "del"], ["moteur"]]},
    {"type": "circuit", "montage": "derivation", "composants": [{"type": "pile", "voltmetre": True}], "branches": [["lampe", "amperemetre"], ["lampe"]]},
    {"type": "graphique", "titre": "Fusion de la glace", "x": {"nom": "Temps", "unite": "min"}, "y": {"nom": "Température", "unite": "°C"},
     "points": [[0, -10], [2, 0], [6, 0], [8, 20]]},
    {"type": "graphique", "x": {"nom": "Intensité", "unite": "A"}, "y": {"nom": "Tension", "unite": "V"},
     "points": [[0.1, 1.0], [0.05, 0.5], [0.2, 2.0]], "style": "points"},
    {"type": "molecule", "formule": "H2O"},
    {"type": "molecule", "formule": "CO₂"},
    {"type": "molecule", "formule": "Cu²⁺"},
    {"type": "reaction", "reactifs": [{"formule": "CH4", "nombre": 1}, {"formule": "O2", "nombre": 2}],
     "produits": [{"formule": "CO2", "nombre": 1}, {"formule": "H2O", "nombre": 2}]},
    {"type": "reaction", "reactifs": ["Fe", {"formule": "H+", "nombre": 2}], "produits": ["Fe2+", "H2"]},
]


@pytest.mark.parametrize("brut", VALIDES)
def test_chaque_schema_se_dessine(brut):
    assert dessiner(valider_figure(brut))[:8] == PNG


def test_catalogue():
    assert set(TYPES) == {"circuit", "graphique", "molecule", "reaction"}
    assert {"H2O", "CO2", "CH4", "O2", "Cu2+", "Cl-", "OH-"} <= set(FORMULES)


def test_noms_par_defaut_des_composants():
    c = valider_figure({"type": "circuit", "montage": "serie", "composants": ["pile", "lampe", "lampe", "moteur", "interrupteur_ferme"]})
    assert [x["nom"] for x in c["composants"]] == ["", "L1", "L2", "M1", "K"]


@pytest.mark.parametrize("brut, message", [
    ({"type": "circuit", "montage": "serie", "composants": ["pile", "pile", "lampe"]}, "exactement une pile"),
    ({"type": "circuit", "montage": "serie", "composants": ["lampe", "moteur"]}, "exactement une pile"),
    ({"type": "circuit", "montage": "serie", "composants": ["pile", "fusée"]}, "Composant inconnu"),
    ({"type": "circuit", "montage": "parallele", "composants": ["pile", "lampe"]}, "montage"),
    ({"type": "circuit", "montage": "derivation", "composants": ["pile"], "branches": [["lampe"]]}, "2 à 3 branches"),
    ({"type": "circuit", "montage": "derivation", "composants": ["lampe"], "branches": [["pile"], ["lampe"]]}, "pile"),
    ({"type": "circuit", "montage": "serie", "composants": ["pile", {"type": "amperemetre", "voltmetre": True}]}, "ampèremètre"),
    ({"type": "circuit", "montage": "serie", "composants": ["pile"] + ["lampe"] * 6}, "2 à 6"),
    ({"type": "graphique", "x": {"nom": "t", "unite": "s"}, "y": {"nom": "d", "unite": "m"}, "points": [[0, 0]]}, "2 à 40 points"),
    ({"type": "graphique", "x": {"nom": "t", "unite": "s"}, "y": {"nom": "d", "unite": "m"}, "points": [[2, 0], [1, 5]]}, "croissants"),
    ({"type": "graphique", "x": {"nom": "t", "unite": "s"}, "y": {"nom": "d", "unite": "m"}, "points": [[0, "dix"], [1, 5]]}, "nombre"),
    ({"type": "graphique", "x": {"unite": "s"}, "y": {"nom": "d"}, "points": [[0, 0], [1, 5]]}, "nom"),
    ({"type": "molecule", "formule": "C6H12O6"}, "non disponible"),
    ({"type": "reaction", "reactifs": [{"formule": "H2", "nombre": 9}], "produits": ["H2O"]}, "1 à 4"),
    ({"type": "reaction", "reactifs": [], "produits": ["H2O"]}, "1 à 4 espèces"),
    ({"type": "cone", "r": 3}, "inconnu"),
])
def test_schema_incoherent_refuse(brut, message):
    with pytest.raises(FigureInvalide, match=message):
        valider_figure(brut)


def test_conservation_des_atomes_verifiable():
    combustion = valider_figure(VALIDES[9])
    assert atomes_de(combustion["reactifs"]) == atomes_de(combustion["produits"]) == {"C": 1, "H": 4, "O": 4}
    fer = valider_figure(VALIDES[10])
    assert atomes_de(fer["reactifs"]) == atomes_de(fer["produits"]) == {"Fe": 1, "H": 2}


@pytest.mark.parametrize("formule, affiche", [("H2O", "H₂O"), ("CO2", "CO₂"), ("Cu2+", "Cu²⁺"), ("Cl-", "Cl⁻"), ("OH-", "OH⁻")])
def test_nom_affiche(formule, affiche):
    assert nom_affiche(formule) == affiche


def test_prompt_decrit_les_schemas_de_physique():
    assert all(f'"type": "{t}"' in T.FIGURES for t in TYPES)
    assert "physique-chimie" in T.SOCLE and "Sécurité" in T.SOCLE and "unité" in T.SPECIFICATIONS["numerique"]
    assert "cone" not in T.FIGURES and "Pythagore" not in T.SOCLE
