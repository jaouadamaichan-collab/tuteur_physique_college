"""Client Anthropic simulé : reconnaît la tâche demandée par le prompt système et répond comme le tuteur."""

import json
import re

from tests.banque import exercice


class Reponse:
    def __init__(self, texte):
        self.content = [type("Bloc", (), {"text": texte, "type": "text"})()]


class FauxClaude:
    appels: list = []
    defaillances: dict = {}     # format -> nombre de réponses invalides à renvoyer avant une valide
    verdict_redaction = "juste"
    indisponible = False
    lecture = {"lisible": True, "matiere": True, "notion": "loi d'additivité des tensions",
               "transcription": "Une pile de 6 V alimente deux lampes L1 et L2 en série. La tension aux bornes de L1 vaut 2,5 V. "
                                "Calcule la tension aux bornes de L2."}
    copies = 0                   # nombre d'exercices qui recopient l'exercice modèle avant un exercice correct
    cartes_invalides = 0         # réponses inutilisables avant de bonnes flashcards

    def __init__(self, api_key=None):
        self.messages = self

    @classmethod
    def reinitialiser(cls):
        cls.appels, cls.defaillances, cls.verdict_redaction, cls.indisponible = [], {}, "juste", False
        cls.lecture, cls.copies, cls.cartes_invalides = dict(FauxClaude.LECTURE), 0, 0

    def create(self, **kw):
        assert "temperature" not in kw, "paramètre refusé par l'API en production"
        FauxClaude.appels.append(kw)
        if FauxClaude.indisponible:
            raise ConnectionError("réseau coupé")
        systeme = kw["system"]
        if "Ta tâche : écrire UN exercice" in systeme:
            format_ = re.search(r'"format": "(\w+)"', systeme).group(1)
            if FauxClaude.defaillances.get(format_, 0) > 0:
                FauxClaude.defaillances[format_] -= 1
                return Reponse("Voici un exercice sympa ! (pas de JSON)")
            ex = exercice(format_)
            if FauxClaude.copies > 0:
                FauxClaude.copies -= 1
                ex["mission"], ex["enonce"] = "", FauxClaude.LECTURE["transcription"]
            return Reponse("```json\n" + json.dumps(ex, ensure_ascii=False) + "\n```")
        if "corriger la réponse rédigée" in systeme:
            return Reponse(json.dumps({"verdict": FauxClaude.verdict_redaction, "retour": "Bien justifié avec les masses volumiques."}))
        if "te pose une question" in systeme:
            return Reponse("Pense à la formule de la masse volumique : ρ = m ÷ V.")
        if "Tu lis la photo" in systeme:
            return Reponse(json.dumps(FauxClaude.lecture, ensure_ascii=False))
        if "écrire des flashcards" in systeme:
            if FauxClaude.cartes_invalides > 0:
                FauxClaude.cartes_invalides -= 1
                return Reponse('{"cartes": [{"recto": "?", "verso": ""}]}')
            return Reponse(json.dumps({"cartes": CARTES}, ensure_ascii=False))
        if "rédiger le bilan" in systeme:
            return Reponse("Bilan : tu maîtrises la vitesse moyenne. Continue !")
        raise AssertionError("prompt inattendu : " + systeme[:80])


FauxClaude.LECTURE = dict(FauxClaude.lecture)

CARTES = [
    {"recto": "Quelle relation donne la masse volumique ρ ?", "verso": "ρ = m ÷ V, en g/mL ou kg/m³.", "figure": None},
    {"recto": "Quelle est la vitesse du son dans l'air ?", "verso": "Environ 340 m/s.", "figure": None},
    {"recto": "Ce montage est-il en série ou en dérivation ?", "verso": "En série : une seule boucle.",
     "figure": {"type": "circuit", "montage": "serie", "composants": ["pile", "lampe", "lampe"]}},
    {"recto": "Quelle est cette molécule ?", "verso": "Le dioxyde de carbone, CO₂.", "figure": {"type": "molecule", "formule": "CO2"}},
    {"recto": "Quel test met en évidence le dioxyde de carbone ?", "verso": "L'eau de chaux se trouble.", "figure": None},
]


def appels_de(tache: str) -> list:
    return [a for a in FauxClaude.appels if tache in a["system"]]
