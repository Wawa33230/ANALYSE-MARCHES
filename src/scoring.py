"""Moteur de scoring : attribue a chaque marche un score de pertinence 0-100
et une categorie (prioritaire / a regarder / hors cible).

Principe :
  - on additionne des bonus (mots-cles cible, CPV, type de marche, bailleur social)
  - on detecte les exclusions "grosse plomberie" MAIS sans jeter un marche qui
    contient un vrai signal "salle de bain / accessibilite" (cas des marches
    multi-lots du type "electricite, plomberie, menuiseries" = France Loire).
  - on signale (sans exclure) les marches orientes carrelage/faience.
"""

from __future__ import annotations

import unicodedata
from datetime import date, datetime
from typing import Iterable

from .models import Tender


def as_text(value) -> str:
    """Convertit n'importe quelle valeur (texte, liste, None...) en chaine de caracteres."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(as_text(v) for v in value)
    return str(value)


def normalize(text) -> str:
    """Minuscule + suppression des accents, pour comparer sans se soucier de la casse."""
    text = as_text(text)
    if not text:
        return ""
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    return text.lower()


def _found(keywords: Iterable[str], haystack: str) -> list[str]:
    """Retourne la liste des mots-cles (normalises) presents dans le texte."""
    hits = []
    for kw in keywords or []:
        nk = normalize(kw)
        if nk and nk in haystack:
            hits.append(kw)
    return hits


def _parse_date(value) -> date | None:
    if not value:
        return None
    s = str(value)
    # On garde juste la partie date (avant un eventuel "T" ou espace)
    s = s.replace("T", " ").split(" ")[0].strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def compute_days_left(tender: Tender) -> int | None:
    d = _parse_date(tender.deadline)
    if not d:
        return None
    return (d - date.today()).days


def score_tender(tender: Tender, scoring_cfg: dict) -> Tender:
    """Calcule score, categorie, mots-cles trouves et drapeaux pour un marche."""

    text = normalize(" ".join([as_text(tender.title), as_text(tender.description), as_text(tender.buyer)]))
    buyer_n = normalize(tender.buyer)
    type_n = normalize(tender.market_type)

    score = 0
    matched: list[str] = []
    flags: list[str] = []

    # 1) Mots-cles prioritaires (coeur du metier) : +18 chacun, plafond 60
    prio_hits = _found(scoring_cfg.get("mots_cles_prioritaires", []), text)
    score += min(len(prio_hits) * 18, 60)
    matched += prio_hits

    # 2) Mots-cles secondaires (contexte plomberie/sanitaire) : +6, plafond 24
    sec_hits = _found(scoring_cfg.get("mots_cles_secondaires", []), text)
    score += min(len(sec_hits) * 6, 24)
    matched += sec_hits

    # 3) Mots-cles "panneaux muraux" (ta specificite) : +12, plafond 24
    pan_hits = _found(scoring_cfg.get("mots_cles_panneaux", []), text)
    score += min(len(pan_hits) * 12, 24)
    matched += pan_hits

    # 4) CPV cibles : bonus selon le bareme du config
    cpv_cfg = scoring_cfg.get("cpv_cibles", {}) or {}
    cpv_codes = [str(c)[:8] for c in (tender.cpv or [])]
    cpv_hit = False
    for code, pts in cpv_cfg.items():
        code8 = str(code)[:8]
        if any(cc.startswith(code8) or code8.startswith(cc[:8]) for cc in cpv_codes):
            score += int(pts)
            cpv_hit = True
            matched.append(f"CPV {code}")

    # 5) Acheteur = bailleur social ? bonus unique +15
    if _found(scoring_cfg.get("indices_bailleur", []), buyer_n):
        score += 15
        flags.append("bailleur social")

    # 6) Type de marche favorable (accord-cadre / bons de commande) : +12
    if _found(scoring_cfg.get("types_favorables", []), type_n + " " + text):
        score += 12
        flags.append("accord-cadre")

    # --- Signal "coeur de cible" : empeche une exclusion abusive ---
    has_core = bool(prio_hits) or cpv_hit or any(
        w in text for w in ("plomberie", "sanitaire", "salle de bain", "salle d'eau", "douche")
    )

    # 7) Exclusions "grosse plomberie" / hors metier
    excl_hits = _found(scoring_cfg.get("mots_cles_exclus", []), text)
    excluded = False
    if excl_hits:
        if has_core:
            # marche multi-lots : on signale seulement, petite penalite plafonnee
            score -= min(len(excl_hits) * 3, 9)
            flags.append("autres lots: " + ", ".join(excl_hits[:3]))
        else:
            # aucun signal salle de bain -> vraiment hors cible
            excluded = True
            flags.append("hors metier: " + ", ".join(excl_hits[:3]))

    # 8) Signal carrelage (tu poses des panneaux, pas du carrelage)
    carr_hits = _found(scoring_cfg.get("mots_cles_carrelage", []), text)
    if carr_hits:
        flags.append("carrelage/faience")
        if not pan_hits:  # carrelage sans alternative panneau -> on retrograde un peu
            score -= 8

    # 9) Mention amiante (frequent sur ce type de marche -> rappel SS4)
    if "amiante" in text:
        flags.append("amiante (SS4)")

    # Bornage 0-100
    score = max(0, min(100, score))

    # Categorisation
    seuil_p = scoring_cfg.get("seuil_prioritaire", 55)
    seuil_a = scoring_cfg.get("seuil_a_regarder", 28)
    if excluded:
        category = "hors_cible"
    elif score >= seuil_p:
        category = "prioritaire"
    elif score >= seuil_a:
        category = "a_regarder"
    else:
        category = "hors_cible"

    tender.score = score
    tender.category = category
    tender.matched = sorted(set(matched), key=lambda x: x.lower())
    tender.flags = flags
    tender.days_left = compute_days_left(tender)
    return tender
