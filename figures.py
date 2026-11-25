"""Schémas de physique-chimie dessinés par le code (comme les figures de géométrie de l'app maths) :
le tuteur décrit le schéma, l'app le vérifie et le dessine. Trois familles :

- circuit   : circuit électrique en série ou en dérivation, symboles normalisés du collège ;
- graphique : courbe ou points de mesure d'une expérience (axes nommés, avec unités) ;
- molecule / reaction : modèles moléculaires (couleurs conventionnelles) et transformations chimiques.

Une description incohérente (deux générateurs, composant inconnu, points mal formés…) est refusée.
"""

from __future__ import annotations

import io
import re

TYPES = ("circuit", "graphique", "molecule", "reaction")


class FigureInvalide(ValueError):
    pass


# ───────────────────────────── Circuits ─────────────────────────────

COMPOSANTS = {
    # type : (préfixe du nom par défaut, description pour le tuteur)
    "pile": ("", "générateur (pile), borne + repérée"),
    "lampe": ("L", "lampe"),
    "moteur": ("M", "moteur"),
    "resistance": ("R", "résistance (conducteur ohmique)"),
    "del": ("D", "diode électroluminescente (DEL), passante dans le sens du courant"),
    "interrupteur_ferme": ("K", "interrupteur fermé"),
    "interrupteur_ouvert": ("K", "interrupteur ouvert"),
    "amperemetre": ("", "ampèremètre (toujours en série)"),
}
MAX_SERIE, MAX_PRINCIPALE, MAX_BRANCHES, MAX_PAR_BRANCHE = 6, 3, 3, 2


def _texte(v, n=14) -> str:
    return str(v or "").strip()[:n]


def _composant(brut, numeros: dict) -> dict:
    if isinstance(brut, str):
        brut = {"type": brut}
    if not isinstance(brut, dict) or brut.get("type") not in COMPOSANTS:
        raise FigureInvalide(f"Composant inconnu : {brut!r}")
    t = brut["type"]
    prefixe = COMPOSANTS[t][0]
    nom = _texte(brut.get("nom"), 6)
    if not nom and prefixe and t not in ("interrupteur_ferme", "interrupteur_ouvert"):
        numeros[prefixe] = numeros.get(prefixe, 0) + 1
        nom = f"{prefixe}{numeros[prefixe]}"
    elif not nom and t.startswith("interrupteur"):
        nom = "K"
    return {"type": t, "nom": nom, "valeur": _texte(brut.get("valeur")), "voltmetre": bool(brut.get("voltmetre"))}


def _valider_circuit(brut: dict) -> dict:
    montage = brut.get("montage")
    if montage not in ("serie", "derivation"):
        raise FigureInvalide("Circuit : montage « serie » ou « derivation » attendu")
    numeros: dict = {}
    principaux = [_composant(c, numeros) for c in (brut.get("composants") or [])]
    branches = []
    if montage == "derivation":
        brutes = brut.get("branches") or []
        if not 2 <= len(brutes) <= MAX_BRANCHES:
            raise FigureInvalide(f"Circuit en dérivation : 2 à {MAX_BRANCHES} branches attendues")
        for b in brutes:
            if not isinstance(b, list) or not 1 <= len(b) <= MAX_PAR_BRANCHE:
                raise FigureInvalide(f"Circuit : chaque branche a 1 à {MAX_PAR_BRANCHE} composants")
            branches.append([_composant(c, numeros) for c in b])
        if len(principaux) > MAX_PRINCIPALE:
            raise FigureInvalide(f"Circuit : au plus {MAX_PRINCIPALE} composants dans la branche principale")
    elif not 2 <= len(principaux) <= MAX_SERIE:
        raise FigureInvalide(f"Circuit en série : 2 à {MAX_SERIE} composants")
    tous = principaux + [c for b in branches for c in b]
    if sum(c["type"] == "pile" for c in tous) != 1:
        raise FigureInvalide("Circuit : il faut exactement une pile")
    if any(c["type"] == "pile" for b in branches for c in b):
        raise FigureInvalide("Circuit : la pile est dans la branche principale")
    if sum(c["voltmetre"] for c in tous) > 2:
        raise FigureInvalide("Circuit : au plus deux voltmètres")
    if any(c["voltmetre"] and c["type"] == "amperemetre" for c in tous):
        raise FigureInvalide("Circuit : pas de voltmètre aux bornes d'un ampèremètre")
    return {"type": "circuit", "montage": montage, "composants": principaux, "branches": branches}


# ───────────────────────────── Graphiques ─────────────────────────────

def _nombre(v, nom):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or abs(v) > 1e9:
        raise FigureInvalide(f"Graphique : {nom} doit être un nombre")
    return float(v)


def _axe(brut, nom) -> dict:
    if not isinstance(brut, dict) or not _texte(brut.get("nom"), 30):
        raise FigureInvalide(f"Graphique : l'axe {nom} doit avoir un nom (et une unité)")
    return {"nom": _texte(brut.get("nom"), 30), "unite": _texte(brut.get("unite"), 10)}


def _valider_graphique(brut: dict) -> dict:
    points = brut.get("points")
    if not isinstance(points, list) or not 2 <= len(points) <= 40:
        raise FigureInvalide("Graphique : 2 à 40 points [x, y] attendus")
    propres = []
    for p in points:
        if not isinstance(p, (list, tuple)) or len(p) != 2:
            raise FigureInvalide("Graphique : chaque point est une paire [x, y]")
        propres.append([_nombre(p[0], "x"), _nombre(p[1], "y")])
    style = brut.get("style") or "courbe"
    if style not in ("courbe", "points"):
        raise FigureInvalide("Graphique : style « courbe » ou « points »")
    if style == "courbe" and any(b[0] <= a[0] for a, b in zip(propres, propres[1:])):
        raise FigureInvalide("Graphique : pour une courbe, les x doivent être croissants")
    return {"type": "graphique", "titre": _texte(brut.get("titre"), 60), "x": _axe(brut.get("x"), "x"),
            "y": _axe(brut.get("y"), "y"), "points": propres, "style": style}


# ───────────────────────────── Molécules ─────────────────────────────

# Atomes : (couleur conventionnelle, rayon, couleur du symbole)
ATOMES = {
    "H": ("#ffffff", 0.30, "#111111"), "C": ("#2f2f2f", 0.42, "#ffffff"), "O": ("#e53935", 0.40, "#ffffff"),
    "N": ("#1e66f5", 0.41, "#ffffff"), "Cl": ("#2e9d4b", 0.50, "#ffffff"), "Na": ("#8e44ad", 0.50, "#ffffff"),
    "Fe": ("#e67e22", 0.50, "#ffffff"), "Cu": ("#b87333", 0.50, "#ffffff"), "Zn": ("#7f8c8d", 0.50, "#ffffff"),
    "S": ("#f1c40f", 0.48, "#111111"),
}
# Modèles : liste d'atomes (symbole, x, y) ; charge pour les ions.
MODELES = {
    "H2": [("H", -0.3, 0), ("H", 0.3, 0)],
    "O2": [("O", -0.38, 0), ("O", 0.38, 0)],
    "N2": [("N", -0.38, 0), ("N", 0.38, 0)],
    "Cl2": [("Cl", -0.45, 0), ("Cl", 0.45, 0)],
    "H2O": [("O", 0, 0.1), ("H", -0.5, -0.3), ("H", 0.5, -0.3)],
    "CO2": [("O", -0.75, 0), ("C", 0, 0), ("O", 0.75, 0)],
    "CO": [("C", -0.38, 0), ("O", 0.38, 0)],
    "CH4": [("C", 0, 0), ("H", 0, 0.55), ("H", 0, -0.55), ("H", -0.55, 0), ("H", 0.55, 0)],
    "NH3": [("N", 0, 0.1), ("H", -0.5, -0.3), ("H", 0.5, -0.3), ("H", 0, 0.62)],
    "HCl": [("H", -0.38, 0), ("Cl", 0.32, 0)],
    "SO2": [("O", -0.72, -0.2), ("S", 0, 0.1), ("O", 0.72, -0.2)],
    "C": [("C", 0, 0)], "O": [("O", 0, 0)], "H": [("H", 0, 0)], "S": [("S", 0, 0)],
    "Fe": [("Fe", 0, 0)], "Cu": [("Cu", 0, 0)], "Zn": [("Zn", 0, 0)], "Na": [("Na", 0, 0)],
}
IONS = {"H+": ("H", "+"), "Na+": ("Na", "+"), "Cl-": ("Cl", "−"), "Cu2+": ("Cu", "2+"), "Fe2+": ("Fe", "2+"),
        "Fe3+": ("Fe", "3+"), "Zn2+": ("Zn", "2+"), "OH-": (None, "−")}
FORMULES = tuple(MODELES) + tuple(IONS)


def _formule(f) -> str:
    f = str(f or "").strip().replace("⁺", "+").replace("⁻", "-").replace("−", "-")
    f = f.translate(str.maketrans("₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹", "01234567890123456789"))
    if f not in FORMULES:
        raise FigureInvalide(f"Molécule ou ion non disponible : {f!r} (disponibles : {', '.join(FORMULES)})")
    return f


def _cote(brut) -> list[dict]:
    if not isinstance(brut, list) or not 1 <= len(brut) <= 4:
        raise FigureInvalide("Réaction : 1 à 4 espèces par côté")
    especes = []
    for e in brut:
        if isinstance(e, str):
            e = {"formule": e, "nombre": 1}
        if not isinstance(e, dict):
            raise FigureInvalide("Réaction : espèce mal décrite")
        n = e.get("nombre", 1)
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= 4:
            raise FigureInvalide("Réaction : nombre de 1 à 4 par espèce")
        especes.append({"formule": _formule(e.get("formule")), "nombre": n})
    if sum(e["nombre"] for e in especes) > 6:
        raise FigureInvalide("Réaction : au plus 6 entités dessinées par côté")
    return especes


def nom_affiche(formule: str) -> str:
    """H2O → H₂O ; Cu2+ → Cu²⁺ ; Cl- → Cl⁻."""
    m = re.fullmatch(r"([A-Za-z0-9]+?)(\d?)([+-])", formule)
    if m:
        base, n, signe = m.groups()
        return base + n.translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹")) + ("⁺" if signe == "+" else "⁻")
    return formule.translate(str.maketrans("0123456789", "₀₁₂₃₄₅₆₇₈₉"))


def atomes_de(especes: list[dict]) -> dict:
    """Atomes d'un côté de la réaction (pour vérifier la conservation, côté tuteur ou tests)."""
    compte: dict = {}
    for e in especes:
        f = e["formule"]
        liste = [a for a, *_ in MODELES[f]] if f in MODELES else ([IONS[f][0]] if IONS[f][0] else ["O", "H"])
        for a in liste:
            compte[a] = compte.get(a, 0) + e["nombre"]
    return compte


# ───────────────────────────── Validation ─────────────────────────────

def valider_figure(brut) -> dict | None:
    """Schéma normalisé, None s'il n'y en a pas, ou FigureInvalide."""
    if brut in (None, {}, ""):
        return None
    if not isinstance(brut, dict) or brut.get("type") not in TYPES:
        raise FigureInvalide(f"Type de schéma inconnu : {brut.get('type') if isinstance(brut, dict) else brut!r}")
    t = brut["type"]
    if t == "circuit":
        return _valider_circuit(brut)
    if t == "graphique":
        return _valider_graphique(brut)
    if t == "molecule":
        return {"type": "molecule", "formule": _formule(brut.get("formule"))}
    return {"type": "reaction", "reactifs": _cote(brut.get("reactifs")), "produits": _cote(brut.get("produits"))}


# ───────────────────────────── Dessin ─────────────────────────────

NOIR, BLEU, GRIS = "#1f2937", "#2563eb", "#94a3b8"
L = 0.9  # longueur occupée par un symbole sur le fil


def _symbole(ax, c: dict, x: float, y: float, vertical: bool):
    """Dessine un composant centré en (x, y), sur un fil horizontal ou vertical. Renvoie ses deux bornes."""
    from matplotlib.patches import Circle, Polygon, Rectangle

    def pt(u, v):  # u le long du fil, v perpendiculaire
        return (x + v, y + u) if vertical else (x + u, y + v)

    a, b = pt(-L / 2, 0), pt(L / 2, 0)
    # masque blanc sur le fil, puis symbole
    if vertical:
        ax.add_patch(Rectangle((x - 0.12, y - L / 2), 0.24, L, color="white", zorder=2))
    else:
        ax.add_patch(Rectangle((x - L / 2, y - 0.12), L, 0.24, color="white", zorder=2))
    t = c["type"]
    trait = {"color": NOIR, "lw": 1.8, "zorder": 3}
    if t in ("lampe", "moteur", "amperemetre"):
        r = 0.26
        ax.plot(*zip(a, pt(-r, 0)), **trait)
        ax.plot(*zip(pt(r, 0), b), **trait)
        ax.add_patch(Circle((x, y), r, fill=True, facecolor="white", edgecolor=NOIR, lw=1.8, zorder=3))
        if t == "lampe":
            d = r * 0.7
            ax.plot([x - d, x + d], [y - d, y + d], **trait)
            ax.plot([x - d, x + d], [y + d, y - d], **trait)
        else:
            ax.text(x, y, "M" if t == "moteur" else "A", ha="center", va="center", fontsize=10, fontweight="bold",
                    color=NOIR, zorder=4)
    elif t == "resistance":
        ax.plot(*zip(a, pt(-0.3, 0)), **trait)
        ax.plot(*zip(pt(0.3, 0), b), **trait)
        w, h = (0.24, 0.6) if vertical else (0.6, 0.24)
        ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, facecolor="white", edgecolor=NOIR, lw=1.8, zorder=3))
    elif t == "pile":
        ax.plot(*zip(a, pt(-0.08, 0)), **trait)
        ax.plot(*zip(pt(0.08, 0), b), **trait)
        ax.plot(*zip(pt(-0.08, -0.3), pt(-0.08, 0.3)), color=NOIR, lw=1.6, zorder=3)   # borne + (trait long)
        ax.plot(*zip(pt(0.08, -0.15), pt(0.08, 0.15)), color=NOIR, lw=4, zorder=3)     # borne − (trait court)
        ax.text(*pt(-0.25, 0.38), "+", ha="center", va="center", fontsize=11, color=NOIR, zorder=4)
    elif t == "del":
        ax.plot(*zip(a, pt(-0.2, 0)), **trait)
        ax.plot(*zip(pt(0.2, 0), b), **trait)
        ax.add_patch(Polygon([pt(-0.2, -0.2), pt(-0.2, 0.2), pt(0.2, 0)], closed=True, facecolor="white",
                             edgecolor=NOIR, lw=1.8, zorder=3))
        ax.plot(*zip(pt(0.2, -0.2), pt(0.2, 0.2)), **trait)
        for k in (-0.05, 0.1):  # flèches de lumière
            ax.annotate("", xy=pt(k + 0.25, 0.5), xytext=pt(k, 0.25),
                        arrowprops={"arrowstyle": "->", "color": NOIR, "lw": 1}, zorder=4)
    elif t.startswith("interrupteur"):
        ax.plot(*zip(a, pt(-0.25, 0)), **trait)
        ax.plot(*zip(pt(0.25, 0), b), **trait)
        fin = pt(0.25, 0.3) if t == "interrupteur_ouvert" else pt(0.25, 0.04)
        ax.plot(*zip(pt(-0.25, 0), fin), **trait)
        for borne in (pt(-0.25, 0), pt(0.25, 0)):   # contacts visibles : un interrupteur fermé ne se confond pas avec le fil
            ax.add_patch(Circle(borne, 0.055, facecolor="white", edgecolor=NOIR, lw=1.5, zorder=4))
    etiquette = " ".join(s for s in (c["nom"], c["valeur"]) if s)
    if etiquette:
        if vertical:   # à gauche du composant, sans toucher le fil
            ax.text(x - 0.42, y, etiquette, ha="right", va="center", fontsize=9, color=BLEU, zorder=4)
        else:
            ax.text(x, y - 0.5, etiquette, ha="center", va="center", fontsize=9, color=BLEU, zorder=4)
    return a, b


def _voltmetre(ax, x: float, y: float, vertical: bool, cote: float):
    """Voltmètre branché aux bornes du composant centré en (x, y), du côté `cote` (+1 ou -1)."""
    from matplotlib.patches import Circle

    d = 0.95 * cote
    if vertical:
        cx, cy, bornes = x + d, y, [(x, y - L / 2), (x, y + L / 2)]
        coins = [(x + d, y - L / 2), (x + d, y + L / 2)]
    else:
        cx, cy, bornes = x, y + d, [(x - L / 2, y), (x + L / 2, y)]
        coins = [(x - L / 2, y + d), (x + L / 2, y + d)]
    for (bx, by), (kx, ky) in zip(bornes, coins):
        ax.plot([bx, kx], [by, ky], color=GRIS, lw=1.3, zorder=1)
        ax.plot([kx, cx], [ky, cy], color=GRIS, lw=1.3, zorder=1)
    ax.add_patch(Circle((cx, cy), 0.26, facecolor="white", edgecolor=NOIR, lw=1.8, zorder=3))
    ax.text(cx, cy, "V", ha="center", va="center", fontsize=10, fontweight="bold", color=NOIR, zorder=4)


def _dessiner_circuit(ax, fig: dict):
    pas = 1.5
    if fig["montage"] == "serie":
        pile = next(c for c in fig["composants"] if c["type"] == "pile")
        autres = [c for c in fig["composants"] if c is not pile]
        haut, bas = autres[: (len(autres) + 1) // 2], autres[(len(autres) + 1) // 2:]
        W, H = pas * (max(len(haut), len(bas), 1) + 1), 2.6
        ax.plot([0, W, W, 0, 0], [0, 0, H, H, 0], color=NOIR, lw=1.8, zorder=1)
        _symbole(ax, pile, 0, H / 2, vertical=True)
        if pile["voltmetre"]:
            _voltmetre(ax, 0, H / 2, True, -1)
        for rang, (ligne, y, cote) in enumerate(((haut, H, 1), (bas, 0, -1))):
            for k, c in enumerate(ligne):
                x = W * (k + 1) / (len(ligne) + 1)
                _symbole(ax, c, x, y, vertical=False)
                if c["voltmetre"]:
                    _voltmetre(ax, x, y, False, cote)
        return
    principaux = fig["composants"]
    pile = next(c for c in principaux if c["type"] == "pile")
    autres = [c for c in principaux if c is not pile]
    hauteur = max(len(b) for b in fig["branches"])
    H = max(2.6, pas * (hauteur + 1))
    x0 = pas * (len(autres) + 1)
    ecart = pas * 1.7 if any(c["nom"] or c["valeur"] for b in fig["branches"] for c in b) else pas * 1.1
    xs = [x0 + ecart * k for k in range(len(fig["branches"]))]
    ax.plot([0, xs[-1]], [H, H], color=NOIR, lw=1.8, zorder=1)
    ax.plot([0, xs[-1]], [0, 0], color=NOIR, lw=1.8, zorder=1)
    ax.plot([0, 0], [0, H], color=NOIR, lw=1.8, zorder=1)
    _symbole(ax, pile, 0, H / 2, vertical=True)
    if pile["voltmetre"]:
        _voltmetre(ax, 0, H / 2, True, -1)
    for k, c in enumerate(autres):
        x = x0 * (k + 1) / (len(autres) + 1)
        _symbole(ax, c, x, H, vertical=False)
        if c["voltmetre"]:
            _voltmetre(ax, x, H, False, 1)
    for x, branche in zip(xs, fig["branches"]):
        ax.plot([x, x], [0, H], color=NOIR, lw=1.8, zorder=1)
        for k, c in enumerate(branche):
            y = H * (len(branche) - k) / (len(branche) + 1)
            _symbole(ax, c, x, y, vertical=True)
            if c["voltmetre"]:
                _voltmetre(ax, x, y, True, 1)
        if x != xs[-1]:  # nœuds (le dernier coin n'en est pas un)
            for y in (0, H):
                ax.plot(x, y, "o", color=NOIR, ms=4, zorder=3)


def _atome(ax, symbole: str, x: float, y: float, charge: str = ""):
    from matplotlib.patches import Circle

    couleur, r, texte = ATOMES[symbole]
    ax.add_patch(Circle((x, y), r, facecolor=couleur, edgecolor=NOIR, lw=1.2, zorder=3))
    ax.text(x, y, symbole, ha="center", va="center", fontsize=8 if len(symbole) > 1 else 9, color=texte,
            fontweight="bold", zorder=4)
    if charge:
        ax.text(x + r * 0.95, y + r * 0.95, charge, ha="center", va="center", fontsize=9, color=NOIR,
                fontweight="bold", zorder=5)


def _entite(ax, formule: str, x: float, y: float) -> float:
    """Dessine une molécule ou un ion centré en x ; renvoie sa demi-largeur."""
    if formule in IONS:
        symbole, charge = IONS[formule]
        if symbole is None:  # OH-
            _atome(ax, "O", x - 0.2, y)
            _atome(ax, "H", x + 0.32, y + 0.1, "")
            ax.text(x + 0.55, y + 0.45, charge, ha="center", va="center", fontsize=9, fontweight="bold", color=NOIR)
            return 0.75
        _atome(ax, symbole, x, y, charge)
        return ATOMES[symbole][1] + 0.15
    largeur = 0.0
    for a, dx, dy in sorted(MODELES[formule], key=lambda t: -ATOMES[t[0]][1]):
        _atome(ax, a, x + dx, y + dy)
        largeur = max(largeur, abs(dx) + ATOMES[a][1])
    return largeur


def _dessiner_reaction(ax, fig: dict):
    x = 0.0

    def cote(especes):
        nonlocal x
        for i, e in enumerate(especes):
            if i:
                ax.text(x + 0.25, 0, "+", ha="center", va="center", fontsize=14, color=NOIR)
                x += 0.5
            for _ in range(e["nombre"]):
                largeur = _largeur(e["formule"])
                _entite(ax, e["formule"], x + largeur, 0)
                x += 2 * largeur + 0.45

    cote(fig["reactifs"])
    ax.annotate("", xy=(x + 0.9, 0), xytext=(x + 0.1, 0), arrowprops={"arrowstyle": "-|>", "color": NOIR, "lw": 1.8})
    x += 1.1
    cote(fig["produits"])
    ax.set_xlim(-0.2, x)
    ax.set_ylim(-1, 1)


def _largeur(formule: str) -> float:
    if formule in IONS:
        symbole = IONS[formule][0]
        return 0.75 if symbole is None else ATOMES[symbole][1] + 0.15
    return max(abs(dx) + ATOMES[a][1] for a, dx, _ in MODELES[formule])


def _dessiner_graphique(ax, fig: dict):
    xs, ys = zip(*fig["points"])
    if fig["style"] == "courbe":
        ax.plot(xs, ys, color=BLEU, lw=2, marker="o", ms=4)
    else:
        ax.plot(xs, ys, linestyle="none", color=BLEU, marker="o", ms=5)
    ax.grid(True, color="#e2e8f0", lw=0.7)
    for cote in ("top", "right"):
        ax.spines[cote].set_visible(False)

    def nom(axe):
        return f"{axe['nom']} ({axe['unite']})" if axe["unite"] else axe["nom"]

    ax.set_xlabel(nom(fig["x"]), fontsize=9)
    ax.set_ylabel(nom(fig["y"]), fontsize=9)
    ax.tick_params(labelsize=8)
    if fig["titre"]:
        ax.set_title(fig["titre"], fontsize=10)


def dessiner(fig: dict) -> bytes:
    """PNG du schéma."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    t = fig["type"]
    taille = {"circuit": (4.6, 3.2), "graphique": (4.2, 3.0), "molecule": (2.0, 1.6), "reaction": (5.4, 1.5)}[t]
    figure, ax = plt.subplots(figsize=taille, dpi=170)
    if t == "graphique":
        _dessiner_graphique(ax, fig)
    else:
        ax.set_aspect("equal")
        ax.axis("off")
        if t == "circuit":
            _dessiner_circuit(ax, fig)
            ax.margins(0.12)
        elif t == "molecule":
            demi = _entite(ax, fig["formule"], 0, 0)
            ax.set_xlim(-demi - 0.25, demi + 0.35)
            ax.set_ylim(-1.35, 0.95)
            ax.text(0, -1.3, nom_affiche(fig["formule"]), ha="center", va="bottom", fontsize=10, color=BLEU)
        else:
            _dessiner_reaction(ax, fig)
    tampon = io.BytesIO()
    figure.savefig(tampon, format="png", bbox_inches="tight", facecolor="white")
    plt.close(figure)
    return tampon.getvalue()
