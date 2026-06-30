"""Modele de donnees commun a toutes les sources : un appel d'offres = un Tender."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class Tender:
    """Un avis d'appel d'offres normalise, quelle que soit sa source."""

    # --- Donnees brutes (remplies par les connecteurs de sources) ---
    id: str                                   # identifiant unique (ex: idweb BOAMP)
    source: str                               # "BOAMP", "TED", "marches-publics.info"...
    title: str                                # objet du marche
    buyer: str = ""                           # nom de l'acheteur (le bailleur)
    department: str = ""                       # code(s) departement, ex "45" ou "45, 18"
    region: str = ""
    market_type: str = ""                      # type de marche / procedure
    cpv: list = field(default_factory=list)    # liste de codes CPV
    publication_date: Optional[str] = None     # AAAA-MM-JJ
    deadline: Optional[str] = None             # AAAA-MM-JJ (date limite de reponse)
    url: str = ""                              # lien direct vers l'avis
    description: str = ""                       # texte complementaire (resume)

    # --- Donnees calculees (remplies par le moteur de scoring) ---
    score: int = 0
    category: str = ""                          # "prioritaire" | "a_regarder" | "hors_cible"
    matched: list = field(default_factory=list)  # mots-cles trouves (pour expliquer le score)
    flags: list = field(default_factory=list)    # alertes : "carrelage", "amiante", "exclusion"...
    days_left: Optional[int] = None              # nombre de jours avant la date limite

    def to_dict(self) -> dict:
        return asdict(self)
